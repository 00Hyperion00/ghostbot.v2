from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ..models import Candle, SignalDecision
from .decision_contract import AIDecisionContract, build_decision_contract, decision_contract_from_provider


@dataclass(slots=True)
class _LoadedModelCandidate:
    model: Any
    model_path: str
    schema_path: str
    feature_schema: Any
    feature_lag: int


def candles_to_frame(candles: Iterable[Candle | dict[str, Any]], *, closed_only: bool = True) -> pd.DataFrame:
    from ..features import candles_to_frame as _candles_to_frame
    return _candles_to_frame(candles, closed_only=closed_only)


def latest_feature_row(df: pd.DataFrame, *, feature_lag: int = 1, feature_columns: list[str] | None = None) -> pd.DataFrame | None:
    from ..features import latest_feature_row as _latest_feature_row
    return _latest_feature_row(df, feature_lag=feature_lag, feature_columns=feature_columns)


@dataclass(slots=True)
class AIProviderConfig:
    model_path: str
    threshold: float = 0.60


class XGBoostSignalProvider:
    def __init__(
        self,
        model_path: str,
        threshold: float = 0.60,
        buy_threshold: float = 0.64,
        sell_threshold: float = 0.57,
        hold_band_low: float = 0.45,
        hold_band_high: float = 0.55,
        indecision_margin: float = 0.08,
        threshold_profile: str = "runtime_settings",
    ) -> None:
        self.model_path = model_path
        self._apply_decision_contract(build_decision_contract(
            threshold=threshold,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            hold_band_low=hold_band_low,
            hold_band_high=hold_band_high,
            indecision_margin=indecision_margin,
            threshold_profile=threshold_profile,
        ))
        self._feature_lag = 1
        self._model = None
        self._load_error: str | None = None
        self._feature_schema = None
        self._schema_path: str | None = None
        self._schema_validated = False
        self._resolved_model_path: str | None = None
        self._last_reload_ok = False
        self._last_reload_error: str | None = None
        self._load_model()

    @property
    def available(self) -> bool:
        return self._model is not None and bool(getattr(self, '_schema_validated', False))

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def last_reload_ok(self) -> bool:
        return bool(getattr(self, '_last_reload_ok', False))

    @property
    def last_reload_error(self) -> str | None:
        return getattr(self, '_last_reload_error', None)

    @property
    def schema_validated(self) -> bool:
        return bool(getattr(self, '_schema_validated', False))

    @property
    def schema_path(self) -> str | None:
        return self._schema_path

    @property
    def schema_version(self) -> str | None:
        schema = getattr(self, '_feature_schema', None)
        return getattr(schema, 'version', None) if schema is not None else None

    @property
    def feature_pack_name(self) -> str | None:
        schema = getattr(self, '_feature_schema', None)
        return getattr(schema, 'feature_pack_name', None) if schema is not None else None

    @property
    def feature_count(self) -> int | None:
        schema = getattr(self, '_feature_schema', None)
        columns = getattr(schema, 'feature_columns', None) if schema is not None else None
        return len(columns) if columns is not None else None

    @property
    def feature_lag(self) -> int:
        return int(getattr(self, '_feature_lag', 1) or 1)

    def _apply_decision_contract(self, contract: AIDecisionContract) -> None:
        validated = contract.validate()
        self.threshold = float(validated.threshold)
        self.buy_threshold = float(validated.buy_threshold)
        self.sell_threshold = float(validated.sell_threshold)
        self.hold_band_low = float(validated.hold_band_low)
        self.hold_band_high = float(validated.hold_band_high)
        self.indecision_margin = float(validated.indecision_margin)
        self.threshold_profile = str(validated.threshold_profile)

    @property
    def decision_contract(self) -> AIDecisionContract:
        return decision_contract_from_provider(self)

    def decision_contract_snapshot(self) -> dict[str, Any]:
        return self.decision_contract.snapshot()

    @property
    def threshold_config(self) -> dict[str, float]:
        return {
            'threshold': float(self.threshold),
            'buy_threshold': float(self.buy_threshold),
            'sell_threshold': float(self.sell_threshold),
            'hold_band_low': float(self.hold_band_low),
            'hold_band_high': float(self.hold_band_high),
            'indecision_margin': float(self.indecision_margin),
        }

    def schema_info(self) -> dict[str, Any]:
        return {
            'model_path': self.model_path,
            'resolved_model_path': self._resolved_model_path,
            'schema_path': self._schema_path,
            'schema_version': self.schema_version,
            'feature_pack_name': self.feature_pack_name,
            'feature_count': self.feature_count,
            'feature_lag': self.feature_lag,
            'schema_validated': self.schema_validated,
            'load_error': self.load_error,
            'last_reload_ok': self.last_reload_ok,
            'last_reload_error': self.last_reload_error,
            'threshold_config': self.threshold_config,
            'threshold_profile': self.threshold_profile,
            'decision_contract': self.decision_contract_snapshot(),
        }

    def _resolve_schema_path(self, model_path: str | Path) -> Path:
        path = Path(model_path)
        return Path(f'{path.with_suffix("")}.schema.json')


    def _validate_schema(self, model: Any, model_path: str | Path) -> Any:
        """Backward-compatible schema validation hook used by tests and diagnostics.

        The reload path uses _load_candidate for atomicity. This method intentionally
        mutates the provider schema fields because older tests and ad-hoc diagnostics
        call it directly to validate a candidate model/schema pair.
        """
        from ..features import FEATURE_COLUMNS
        from ..training.feature_schema import read_feature_schema

        schema_path = self._resolve_schema_path(model_path)
        self._schema_path = schema_path.as_posix()
        self._schema_validated = False
        if not schema_path.exists():
            self._feature_schema = None
            self._feature_lag = 1
            raise FileNotFoundError(f'Feature schema sidecar not found: {schema_path}')

        schema = read_feature_schema(schema_path)
        try:
            schema.validate_feature_columns(list(FEATURE_COLUMNS))
            booster = getattr(model, 'get_booster', lambda: None)()
            booster_names = getattr(booster, 'feature_names', None) if booster is not None else None
            if booster_names:
                schema.validate_feature_columns(list(booster_names))
        except Exception:
            self._feature_schema = schema
            self._feature_lag = int(getattr(schema, 'feature_lag', 1) or 1)
            self._schema_validated = False
            raise

        self._feature_schema = schema
        self._feature_lag = int(getattr(schema, 'feature_lag', 1) or 1)
        self._schema_validated = True
        self._load_error = None
        return schema

    def _load_candidate(self, model_path: str | Path) -> _LoadedModelCandidate:
        from ..features import FEATURE_COLUMNS
        from ..training.feature_schema import read_feature_schema
        import xgboost as xgb

        resolved_model_path = Path(model_path)
        schema_path = self._resolve_schema_path(resolved_model_path)
        if not resolved_model_path.exists():
            raise FileNotFoundError(f'AI model file not found: {resolved_model_path}')
        if not schema_path.exists():
            raise FileNotFoundError(f'Feature schema sidecar not found: {schema_path}')

        model = xgb.XGBClassifier()
        model.load_model(resolved_model_path.as_posix())
        schema = read_feature_schema(schema_path)
        schema.validate_feature_columns(list(FEATURE_COLUMNS))
        booster = getattr(model, 'get_booster', lambda: None)()
        booster_names = getattr(booster, 'feature_names', None) if booster is not None else None
        if booster_names:
            schema.validate_feature_columns(list(booster_names))
        return _LoadedModelCandidate(
            model=model,
            model_path=resolved_model_path.as_posix(),
            schema_path=schema_path.as_posix(),
            feature_schema=schema,
            feature_lag=int(schema.feature_lag or 1),
        )

    def _commit_candidate(self, candidate: _LoadedModelCandidate) -> None:
        self._model = candidate.model
        self.model_path = candidate.model_path
        self._resolved_model_path = candidate.model_path
        self._schema_path = candidate.schema_path
        self._feature_schema = candidate.feature_schema
        self._feature_lag = candidate.feature_lag
        self._schema_validated = True
        self._load_error = None
        self._last_reload_ok = True
        self._last_reload_error = None

    def _clear_loaded_model(self, error: str | None = None) -> None:
        self._model = None
        self._feature_schema = None
        self._schema_validated = False
        self._schema_path = None
        self._load_error = error
        self._last_reload_ok = False
        self._last_reload_error = error

    def _load_model(self) -> bool:
        self._resolved_model_path = str(self.model_path)
        try:
            candidate = self._load_candidate(self.model_path)
            self._commit_candidate(candidate)
            return True
        except Exception as exc:  # pragma: no cover
            self._clear_loaded_model(str(exc))
            return False

    def reload(
        self,
        *,
        model_path: str | None = None,
        threshold: float | None = None,
        buy_threshold: float | None = None,
        sell_threshold: float | None = None,
        hold_band_low: float | None = None,
        hold_band_high: float | None = None,
        indecision_margin: float | None = None,
        threshold_profile: str | None = None,
    ) -> bool:
        candidate_path = model_path or self.model_path
        try:
            candidate_contract = build_decision_contract(
                threshold=threshold,
                buy_threshold=buy_threshold,
                sell_threshold=sell_threshold,
                hold_band_low=hold_band_low,
                hold_band_high=hold_band_high,
                indecision_margin=indecision_margin,
                threshold_profile=threshold_profile,
                fallback=self.decision_contract,
            )
            candidate = self._load_candidate(candidate_path)
        except Exception as exc:
            # Atomic reload: keep the currently loaded model/schema intact and report the failure.
            self._load_error = str(exc)
            self._last_reload_ok = False
            self._last_reload_error = str(exc)
            if self._model is None:
                self._schema_validated = False
            return False

        self._apply_decision_contract(candidate_contract)
        self._commit_candidate(candidate)
        return bool(self.available)

    def _schema_columns(self) -> list[str]:
        schema = getattr(self, '_feature_schema', None)
        columns = getattr(schema, 'feature_columns', None) if schema is not None else None
        if columns:
            return [str(col) for col in columns]
        from ..features import FEATURE_COLUMNS
        return list(FEATURE_COLUMNS)

    def _hold_unavailable(self) -> SignalDecision:
        return SignalDecision(
            signal='HOLD',
            trend='UNKNOWN',
            reason=f'AI model unavailable: {self._load_error or "schema not validated"}',
            provider='ai',
            confidence=0.0,
            metrics={'schemaValidated': self.schema_validated, 'loadError': self._load_error},
        )

    def predict(self, candles: Iterable[Candle | dict], *, symbol: str = '', interval: str = '') -> SignalDecision:
        if not self.available:
            return self._hold_unavailable()

        df = candles_to_frame(candles, closed_only=True)
        if len(df) < 30:
            return SignalDecision(signal='HOLD', trend='UNKNOWN', reason='AI Kararı | Yetersiz mum', provider='ai', confidence=0.0)
        columns = self._schema_columns()
        try:
            row = latest_feature_row(df, feature_lag=self.feature_lag, feature_columns=columns)
        except TypeError:
            # Backward-compatible hook for older unit tests that monkeypatch latest_feature_row
            # with a two-argument callable. The schema order is still enforced below.
            row = latest_feature_row(df, feature_lag=self.feature_lag)
        if row is None:
            return SignalDecision(signal='HOLD', trend='UNKNOWN', reason='AI Kararı | Feature satırı üretilemedi', provider='ai', confidence=0.0)
        try:
            row = row.loc[:, columns].astype('float32')
        except Exception as exc:
            return SignalDecision(signal='HOLD', trend='UNKNOWN', reason=f'AI Kararı | Feature schema mismatch: {exc}', provider='ai', confidence=0.0)
        if row.isna().any(axis=None):
            return SignalDecision(signal='HOLD', trend='UNKNOWN', reason='AI Kararı | Feature satırında NaN var', provider='ai', confidence=0.0)

        probabilities = self._model.predict_proba(row)[0]
        hold_p, buy_p, sell_p = (float(probabilities[0]), float(probabilities[1]), float(probabilities[2]))
        predicted_class = max(range(3), key=lambda idx: probabilities[idx])
        raw_signal = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}.get(predicted_class, 'HOLD')
        confidence = float(probabilities[predicted_class])
        margin = abs(buy_p - sell_p)

        signal = 'HOLD'
        calibration_reason = 'RAW_TOP_HOLD'
        action_floor = self.hold_band_low
        raw_buy_accept = raw_signal == 'BUY' and buy_p >= action_floor and buy_p > hold_p and margin >= self.indecision_margin
        raw_sell_accept = raw_signal == 'SELL' and sell_p >= action_floor and sell_p > hold_p and margin >= self.indecision_margin

        if raw_buy_accept:
            signal = 'BUY'
            calibration_reason = 'RAW_ACTION_FIRST_ACCEPT'
        elif raw_sell_accept:
            signal = 'SELL'
            calibration_reason = 'RAW_ACTION_FIRST_ACCEPT'
        elif raw_signal == 'BUY' and buy_p >= self.buy_threshold:
            signal = 'BUY'
            calibration_reason = 'RAW_ACTION_HIGH_BAND_ACCEPT'
        elif raw_signal == 'SELL' and sell_p >= self.sell_threshold:
            signal = 'SELL'
            calibration_reason = 'RAW_ACTION_HIGH_BAND_ACCEPT'
        else:
            signal = 'HOLD'
            if raw_signal != 'HOLD' and hold_p >= self.hold_band_high:
                calibration_reason = 'REJECT_HOLD_DOMINANCE'
            elif margin < self.indecision_margin:
                calibration_reason = 'REJECT_LOW_MARGIN'
            elif raw_signal != 'HOLD':
                calibration_reason = 'REJECT_LOW_ACTION_PROB'

        ema9 = float(row['EMA_9'].iloc[0]) if 'EMA_9' in row.columns else 0.0
        ema21 = float(row['EMA_21'].iloc[0]) if 'EMA_21' in row.columns else 0.0
        trend = 'UP' if ema9 > ema21 else 'DOWN'
        return SignalDecision(
            signal=signal,
            trend=trend,
            reason=f'AI Kararı | Güven Skoru: %{confidence * 100:.1f}',
            provider='ai',
            confidence=confidence,
            metrics={
                'emaFast': ema9,
                'emaSlow': ema21,
                'rawPredictedClass': predicted_class,
                'calibratedClass': {'HOLD': 0, 'BUY': 1, 'SELL': 2}[signal],
                'calibrationReason': calibration_reason,
                'buyProbability': buy_p,
                'sellProbability': sell_p,
                'holdProbability': hold_p,
                'rawTopProbability': confidence,
                'rawMargin': margin,
                'schemaValidated': self.schema_validated,
                'schemaVersion': self.schema_version,
                'featurePackName': self.feature_pack_name,
                'featureCount': self.feature_count,
                'featureLag': self.feature_lag,
            },
            last_evaluated_close_time=int(df.iloc[-1]['close_time']) if 'close_time' in df.columns else None,
        )
