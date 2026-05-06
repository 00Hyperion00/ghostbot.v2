from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import log2
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from tradebot.cost_aware_label_policy_recovery import (
    CostAwareLabelPolicyCandidate,
    default_cost_aware_label_policy_candidates,
)
from tradebot.features import FEATURE_COLUMNS, clean_feature_frame
from tradebot.features import get_default_feature_schema
from tradebot.training.calibration import (
    apply_threshold_calibration,
    calibrate_prediction_decision,
    get_threshold_config,
    summarize_prediction_distribution,
    summarize_threshold_calibration,
)
from tradebot.training.class_balance import build_sample_weights, serialize_class_weight_map
from tradebot.training.dataset_manifest import build_dataset_manifest, write_dataset_manifest
from tradebot.training.feature_schema import write_feature_schema
from tradebot.training.labeling import build_cost_aware_atr_targets

COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION = "4B.4.3.6.6.24J"
TARGET_NAMES = {0: "HOLD", 1: "BUY", 2: "SELL"}
ACTION_CLASS_IDS = (1, 2)


@dataclass(frozen=True, slots=True)
class CostAwareRetrainCandidateSpec:
    label_policy: CostAwareLabelPolicyCandidate
    class_weight_profile: str = "balanced"
    threshold_profile: str = "balanced"
    feature_lag: int | None = None
    max_depth: int = 3
    n_estimators: int = 18
    learning_rate: float = 0.05

    def slug(self) -> str:
        lag = "auto" if self.feature_lag is None else str(int(self.feature_lag))
        parts = [
            self.label_policy.name,
            str(self.class_weight_profile),
            str(self.threshold_profile),
            f"lag{lag}",
        ]
        return "_".join(str(part).replace(" ", "_") for part in parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_policy": self.label_policy.to_dict(),
            "class_weight_profile": str(self.class_weight_profile),
            "threshold_profile": str(self.threshold_profile),
            "feature_lag": self.feature_lag,
            "max_depth": int(self.max_depth),
            "n_estimators": int(self.n_estimators),
            "learning_rate": float(self.learning_rate),
        }


@dataclass(frozen=True, slots=True)
class CostAwareRetrainGateLimits:
    min_clean_samples: int = 1_000
    min_target_action_pct: float = 8.0
    max_target_action_pct: float = 45.0
    min_target_hold_pct: float = 35.0
    max_target_action_side_pct: float = 76.0
    min_validation_action_classes: int = 2
    min_raw_action_pct: float = 2.0
    max_raw_action_pct: float = 70.0
    min_calibrated_action_pct: float = 1.0
    max_calibrated_action_pct: float = 45.0
    max_calibrated_action_side_pct: float = 82.0
    max_low_margin_rejection_pct: float = 75.0
    min_buy_sell_margin_mean: float = 0.012
    min_buy_sell_margin_median: float = 0.010
    min_action_hold_margin_mean: float = 0.010
    min_directional_entropy: float = 0.62
    min_accuracy: float = 0.30
    min_calibrated_accuracy: float = 0.30
    target_calibrated_action_pct: float = 18.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(parsed):
        return default
    return parsed


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed


def _append_unique(target: list[str], code: str) -> None:
    if code not in target:
        target.append(code)


def _pct(part: int | float, total: int | float) -> float:
    total_f = float(total or 0.0)
    if total_f <= 0.0:
        return 0.0
    return round((float(part) / total_f) * 100.0, 6)


def _summary(values: Iterable[Any]) -> dict[str, float]:
    vals = sorted(_safe_float(v) for v in values if v is not None and np.isfinite(_safe_float(v)))
    if not vals:
        return {"min": 0.0, "median": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "min": round(float(vals[0]), 8),
        "median": round(float(median(vals)), 8),
        "mean": round(float(mean(vals)), 8),
        "max": round(float(vals[-1]), 8),
    }


def _class_distribution(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(_safe_int(v, 0) for v in values)
    return {name: int(counts.get(cls, 0)) for cls, name in TARGET_NAMES.items()}


def _class_distribution_from_map(raw: Mapping[str, Any] | Mapping[int, Any] | None) -> dict[str, int]:
    if not isinstance(raw, Mapping):
        return {"HOLD": 0, "BUY": 0, "SELL": 0}
    out = {"HOLD": 0, "BUY": 0, "SELL": 0}
    for key, value in raw.items():
        cls = _safe_int(key, 0) if str(key) in {"0", "1", "2"} else None
        if cls is None:
            cls = {"HOLD": 0, "BUY": 1, "SELL": 2}.get(str(key).upper())
        if cls in TARGET_NAMES:
            out[TARGET_NAMES[int(cls)]] = max(0, _safe_int(value, 0))
    return out


def _action_pct(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    hold = _safe_int(distribution.get("HOLD"), 0)
    return _pct(buy + sell, buy + sell + hold)


def _hold_pct(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    hold = _safe_int(distribution.get("HOLD"), 0)
    return _pct(hold, buy + sell + hold)


def _dominant_action_pct(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    total = buy + sell
    if total <= 0:
        return 0.0
    return _pct(max(buy, sell), total)


def _directional_entropy(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    total = buy + sell
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in (buy, sell):
        if count > 0:
            p = count / total
            entropy -= p * log2(p)
    return round(float(entropy), 6)


def _sidecar_paths(model_path: Path) -> tuple[Path, Path]:
    stem = model_path.with_suffix("")
    return Path(f"{stem}.schema.json"), Path(f"{stem}.manifest.json")


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {"openTime": "open_time", "closeTime": "close_time", "quoteVolume": "quote_volume"}
    out = out.rename(columns={key: val for key, val in rename.items() if key in out.columns})
    for col in ("open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"):
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.sort_values("close_time" if "close_time" in out.columns else "open_time").reset_index(drop=True)


def _training_matrix(labeled: pd.DataFrame, feature_columns: Sequence[str]) -> tuple[pd.DataFrame, pd.Series]:
    clean = clean_feature_frame(labeled, require_target=True, feature_columns=list(feature_columns))
    if clean.empty:
        raise RuntimeError("No clean cost-aware training matrix produced")
    return clean[list(feature_columns)].astype("float32"), clean["target"].astype("int64")


def _calibration_reasons(proba: np.ndarray, raw_pred: np.ndarray, *, threshold_profile: str) -> list[str]:
    cfg = get_threshold_config(threshold_profile)
    reasons: list[str] = []
    for probs, pred in zip(proba, raw_pred, strict=False):
        _decision, reason = calibrate_prediction_decision(
            probs,
            raw_pred=int(pred),
            buy_threshold=cfg.buy_threshold,
            sell_threshold=cfg.sell_threshold,
            hold_band_low=cfg.hold_band_low,
            hold_band_high=cfg.hold_band_high,
            indecision_margin=cfg.indecision_margin,
        )
        reasons.append(str(reason))
    return reasons


def evaluate_cost_aware_training_result(
    result: Mapping[str, Any] | None,
    *,
    limits: CostAwareRetrainGateLimits | None = None,
) -> dict[str, Any]:
    limits = limits or CostAwareRetrainGateLimits()
    result = dict(result or {})
    reasons: list[str] = []
    warnings: list[str] = []

    clean_samples = _safe_int(result.get("clean_samples"), 0)
    target_distribution = _class_distribution_from_map(result.get("target_distribution"))
    validation_actual_distribution = _class_distribution_from_map(result.get("validation_actual_class_distribution"))
    raw_distribution = _class_distribution_from_map(result.get("validation_predicted_class_distribution"))
    calibrated_distribution = _class_distribution_from_map(result.get("calibrated_predicted_class_distribution"))

    target_action_pct = _action_pct(target_distribution)
    target_hold_pct = _hold_pct(target_distribution)
    target_side_pct = _dominant_action_pct(target_distribution)
    target_entropy = _directional_entropy(target_distribution)
    raw_action_pct = _action_pct(raw_distribution)
    raw_side_pct = _dominant_action_pct(raw_distribution)
    calibrated_action_pct = _action_pct(calibrated_distribution)
    calibrated_side_pct = _dominant_action_pct(calibrated_distribution)
    actual_action_classes = int(sum(1 for side in ("BUY", "SELL") if _safe_int(validation_actual_distribution.get(side), 0) > 0))

    sep = result.get("probability_separation") if isinstance(result.get("probability_separation"), Mapping) else {}
    buy_sell_margin = sep.get("buy_sell_margin") if isinstance(sep.get("buy_sell_margin"), Mapping) else {}
    action_hold_margin = sep.get("action_hold_margin") if isinstance(sep.get("action_hold_margin"), Mapping) else {}
    buy_sell_margin_mean = _safe_float(buy_sell_margin.get("mean"), 0.0)
    buy_sell_margin_median = _safe_float(buy_sell_margin.get("median"), 0.0)
    action_hold_margin_mean = _safe_float(action_hold_margin.get("mean"), 0.0)

    reason_counts = result.get("calibrated_reason_counts") if isinstance(result.get("calibrated_reason_counts"), Mapping) else {}
    total_val = max(1, int(sum(_safe_int(v, 0) for v in calibrated_distribution.values())))
    low_margin_rejection_pct = _pct(_safe_int(reason_counts.get("REJECT_LOW_MARGIN"), 0), total_val)

    accuracy = _safe_float(result.get("accuracy"), 0.0)
    calibrated_accuracy = _safe_float(result.get("calibrated_accuracy"), 0.0)

    if clean_samples < limits.min_clean_samples:
        _append_unique(reasons, "CLEAN_SAMPLE_COUNT_LOW")
    if target_action_pct < limits.min_target_action_pct:
        _append_unique(reasons, "TARGET_ACTION_COVERAGE_LOW")
    if target_action_pct > limits.max_target_action_pct:
        _append_unique(reasons, "TARGET_ACTION_COVERAGE_HIGH")
    if target_hold_pct < limits.min_target_hold_pct:
        _append_unique(reasons, "TARGET_HOLD_COVERAGE_LOW")
    if target_side_pct > limits.max_target_action_side_pct:
        _append_unique(reasons, "TARGET_ACTION_SIDE_IMBALANCE_HIGH")
    if target_entropy < limits.min_directional_entropy:
        _append_unique(reasons, "TARGET_DIRECTIONAL_ENTROPY_LOW")
    if actual_action_classes < limits.min_validation_action_classes:
        _append_unique(reasons, "VALIDATION_ACTION_CLASS_COVERAGE_LOW")
    if raw_action_pct < limits.min_raw_action_pct:
        _append_unique(reasons, "VALIDATION_RAW_ACTION_COVERAGE_LOW")
    if raw_action_pct > limits.max_raw_action_pct:
        _append_unique(reasons, "VALIDATION_RAW_ACTION_COVERAGE_HIGH")
    if raw_side_pct > limits.max_calibrated_action_side_pct:
        _append_unique(reasons, "VALIDATION_RAW_ACTION_SIDE_IMBALANCE_HIGH")
    if calibrated_action_pct < limits.min_calibrated_action_pct:
        _append_unique(reasons, "VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW")
    if calibrated_action_pct > limits.max_calibrated_action_pct:
        _append_unique(reasons, "VALIDATION_CALIBRATED_ACTION_COVERAGE_HIGH")
    if calibrated_side_pct > limits.max_calibrated_action_side_pct:
        _append_unique(reasons, "VALIDATION_CALIBRATED_ACTION_SIDE_IMBALANCE_HIGH")
    if low_margin_rejection_pct > limits.max_low_margin_rejection_pct:
        _append_unique(reasons, "LOW_MARGIN_REJECTION_HIGH")
    if buy_sell_margin_mean < limits.min_buy_sell_margin_mean:
        _append_unique(reasons, "BUY_SELL_SEPARATION_MEAN_LOW")
    if buy_sell_margin_median < limits.min_buy_sell_margin_median:
        _append_unique(reasons, "BUY_SELL_SEPARATION_MEDIAN_LOW")
    if action_hold_margin_mean < limits.min_action_hold_margin_mean:
        _append_unique(reasons, "ACTION_HOLD_SEPARATION_MEAN_LOW")
    if accuracy < limits.min_accuracy:
        _append_unique(reasons, "VALIDATION_RAW_ACCURACY_LOW")
    if calibrated_accuracy < limits.min_calibrated_accuracy:
        _append_unique(reasons, "VALIDATION_CALIBRATED_ACCURACY_LOW")
    if bool(result.get("synthetic_class_padding_applied", False)):
        _append_unique(reasons, "SYNTHETIC_CLASS_PADDING_USED")

    if calibrated_action_pct > 0.0 and calibrated_action_pct < limits.min_calibrated_action_pct * 2.0:
        _append_unique(warnings, "CALIBRATED_ACTION_COVERAGE_NEAR_FLOOR")
    if target_action_pct > limits.max_target_action_pct * 0.85:
        _append_unique(warnings, "TARGET_ACTION_COVERAGE_NEAR_CEILING")

    decision = "BLOCK" if reasons else ("WARN" if warnings else "PASS")
    metrics = {
        "clean_samples": clean_samples,
        "target_distribution": target_distribution,
        "target_action_pct": target_action_pct,
        "target_hold_pct": target_hold_pct,
        "target_action_side_pct": target_side_pct,
        "target_directional_entropy": target_entropy,
        "validation_actual_distribution": validation_actual_distribution,
        "validation_raw_distribution": raw_distribution,
        "validation_raw_action_pct": raw_action_pct,
        "validation_raw_action_side_pct": raw_side_pct,
        "validation_calibrated_distribution": calibrated_distribution,
        "validation_calibrated_action_pct": calibrated_action_pct,
        "validation_calibrated_action_side_pct": calibrated_side_pct,
        "low_margin_rejection_pct": low_margin_rejection_pct,
        "buy_sell_margin_mean": round(buy_sell_margin_mean, 8),
        "buy_sell_margin_median": round(buy_sell_margin_median, 8),
        "action_hold_margin_mean": round(action_hold_margin_mean, 8),
        "accuracy": round(accuracy, 8),
        "calibrated_accuracy": round(calibrated_accuracy, 8),
        "label_policy": result.get("label_policy") or {},
        "class_weight_profile": result.get("class_weight_profile"),
        "threshold_profile": result.get("threshold_profile"),
    }
    return {
        "contract_version": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
        "report_type": "cost_aware_retrain_candidate_gate",
        "decision": decision,
        "ok": decision != "BLOCK",
        "approved_for_training_candidate": decision == "PASS",
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reload_allowed": False,
        "model_path": result.get("model_path") or result.get("output"),
        "candidate_spec": result.get("candidate_spec") or {},
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": metrics,
        "limits": limits.to_dict(),
        "score": rank_cost_aware_training_result(result, metrics=metrics, decision=decision),
    }


def rank_cost_aware_training_result(result: Mapping[str, Any] | None, *, metrics: Mapping[str, Any] | None = None, decision: str | None = None) -> float:
    result = dict(result or {})
    metrics = dict(metrics or {})
    calibrated_action_pct = _safe_float(metrics.get("validation_calibrated_action_pct"), 0.0)
    target_action = _safe_float(metrics.get("target_action_pct"), 0.0)
    target = _safe_float(metrics.get("limits_target_calibrated_action_pct") or 18.0, 18.0)
    accuracy = _safe_float(metrics.get("calibrated_accuracy"), _safe_float(result.get("calibrated_accuracy"), 0.0))
    mean_sep = _safe_float(metrics.get("buy_sell_margin_mean"), 0.0)
    action_hold = _safe_float(metrics.get("action_hold_margin_mean"), 0.0)
    low_margin = _safe_float(metrics.get("low_margin_rejection_pct"), 100.0)
    side = _safe_float(metrics.get("validation_calibrated_action_side_pct"), 100.0)
    penalty = 0.0
    if decision == "BLOCK":
        penalty += 100.0
    elif decision == "WARN":
        penalty += 10.0
    penalty += abs(calibrated_action_pct - target) * 1.5
    penalty += max(0.0, side - 65.0) * 0.8
    penalty += low_margin * 0.4
    return round(float((accuracy * 100.0) + (mean_sep * 500.0) + (action_hold * 250.0) + (target_action * 0.25) - penalty), 6)


def train_cost_aware_candidate(
    df: pd.DataFrame,
    spec: CostAwareRetrainCandidateSpec,
    *,
    symbol: str = "ETHUSDT",
    interval: str = "1m",
    days: int = 0,
    model_dir: str | Path = "models/4B436624J_candidates",
) -> dict[str, Any]:
    import xgboost as xgb

    schema = get_default_feature_schema()
    if spec.feature_lag is not None:
        schema.feature_lag = int(spec.feature_lag)
    source = _normalize_ohlcv(df)
    labeled = build_cost_aware_atr_targets(source, config=spec.label_policy.to_label_config(), feature_lag=schema.feature_lag)
    if labeled.empty:
        raise RuntimeError("No cost-aware labeled samples produced")
    raw_target_distribution = {str(int(k)): int(v) for k, v in labeled["target"].value_counts().sort_index().to_dict().items()}
    present_classes = {int(v) for v in labeled["target"].dropna().astype(int).unique().tolist()}
    synthetic_class_padding_applied = False
    if len(present_classes) < 3:
        # Multi-class XGBoost expects all classes. We make this explicit and gate it out later.
        dummy = labeled.iloc[-3:].copy()
        dummy["target"] = [0, 1, 2]
        dummy["synthetic_class_padding"] = True
        labeled = labeled.copy()
        labeled["synthetic_class_padding"] = False
        labeled = pd.concat([labeled, dummy], ignore_index=True)
        synthetic_class_padding_applied = True

    X, y = _training_matrix(labeled, schema.feature_columns)
    if len(X) < 50:
        raise RuntimeError("Cost-aware training matrix too small")
    weights, weight_map = build_sample_weights(y.tolist(), profile=spec.class_weight_profile)
    X_train, X_test, y_train, y_test, w_train, _w_test = train_test_split(X, y, weights, test_size=0.2, shuffle=False)
    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        learning_rate=float(spec.learning_rate),
        max_depth=int(spec.max_depth),
        n_estimators=int(spec.n_estimators),
        subsample=0.85,
        colsample_bytree=0.85,
        n_jobs=1,
        tree_method="hist",
    )
    model.fit(X_train, y_train, sample_weight=w_train, eval_set=[(X_test, y_test)], verbose=False)
    proba = np.asarray(model.predict_proba(X_test), dtype=float)
    raw_pred = np.asarray(proba.argmax(axis=1), dtype=int)
    threshold_cfg = get_threshold_config(spec.threshold_profile)
    calibrated_pred = apply_threshold_calibration(
        proba,
        raw_pred=raw_pred,
        buy_threshold=threshold_cfg.buy_threshold,
        sell_threshold=threshold_cfg.sell_threshold,
        hold_band_low=threshold_cfg.hold_band_low,
        hold_band_high=threshold_cfg.hold_band_high,
        indecision_margin=threshold_cfg.indecision_margin,
    )
    reasons = _calibration_reasons(proba, raw_pred, threshold_profile=spec.threshold_profile)
    reason_counts = dict(sorted(Counter(reasons).items()))
    buy_sell_margin = np.abs(proba[:, 1] - proba[:, 2])
    action_hold_margin = np.maximum(proba[:, 1], proba[:, 2]) - proba[:, 0]

    raw_prediction_distribution = summarize_prediction_distribution(y_test, raw_pred, proba)
    calibration_report = summarize_threshold_calibration(y_test, proba, raw_pred=raw_pred, profile=spec.threshold_profile)
    out_dir = Path(model_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / f"{str(symbol).upper()}_model_4b436624J_{spec.slug()}.ubj"
    model.save_model(model_path.as_posix())
    schema_path, manifest_path = _sidecar_paths(model_path)
    write_feature_schema(schema_path, schema)
    clean_labeled = clean_feature_frame(labeled, require_target=True, feature_columns=schema.feature_columns)
    manifest = build_dataset_manifest(
        symbol=str(symbol).upper(),
        interval=str(interval),
        days=int(days or 0),
        schema_version=schema.version,
        feature_columns=schema.feature_columns,
        raw_df=source,
        labeled_df=labeled,
        clean_df=clean_labeled,
        target_distribution=y.value_counts().sort_index().to_dict(),
        label_config=spec.label_policy.to_label_config().to_dict() | {"policy_name": spec.label_policy.name, "feature_lag": schema.feature_lag},
        feature_pack_name=schema.feature_pack_name,
        class_weight_profile=spec.class_weight_profile,
        class_weight_map=serialize_class_weight_map(weight_map),
        threshold_profile=spec.threshold_profile,
        threshold_config=threshold_cfg.to_dict(),
    )
    manifest["workflow_version"] = COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION
    manifest["candidate_spec"] = spec.to_dict()
    write_dataset_manifest(manifest_path, manifest)
    validation_actual = raw_prediction_distribution.get("actual_class_distribution") or {}
    validation_raw = raw_prediction_distribution.get("predicted_class_distribution") or {}
    validation_cal = calibration_report.get("calibrated_predicted_class_distribution") or {}

    return {
        "contract_version": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
        "workflow_version": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
        "candidate_spec": spec.to_dict(),
        "symbol": str(symbol).upper(),
        "interval": str(interval),
        "days": int(days or 0),
        "model_path": model_path.as_posix(),
        "output": model_path.as_posix(),
        "schema_path": schema_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "sidecars_written": True,
        "accuracy": float(accuracy_score(y_test, raw_pred)),
        "calibrated_accuracy": float(accuracy_score(y_test, calibrated_pred)),
        "samples": int(len(labeled)),
        "clean_samples": int(len(clean_labeled)),
        "feature_schema_version": schema.version,
        "feature_pack_name": schema.feature_pack_name,
        "feature_columns": list(schema.feature_columns),
        "feature_lag": int(schema.feature_lag),
        "class_weight_profile": str(spec.class_weight_profile),
        "threshold_profile": str(spec.threshold_profile),
        "threshold_config": threshold_cfg.to_dict(),
        "class_weight_map": serialize_class_weight_map(weight_map),
        "label_policy": spec.label_policy.to_dict(),
        "target_distribution": raw_target_distribution,
        "training_target_distribution": {str(int(k)): int(v) for k, v in y.value_counts().sort_index().to_dict().items()},
        "synthetic_class_padding_applied": bool(synthetic_class_padding_applied),
        "validation_actual_class_distribution": {str(k): int(v) for k, v in validation_actual.items()},
        "validation_predicted_class_distribution": {str(k): int(v) for k, v in validation_raw.items()},
        "calibrated_predicted_class_distribution": {str(k): int(v) for k, v in validation_cal.items()},
        "prediction_distribution": raw_prediction_distribution,
        "calibrated_action_report": calibration_report.get("calibrated_action_report") or {},
        "calibrated_reason_counts": reason_counts,
        "probability_separation": {
            "buy_sell_margin": _summary(buy_sell_margin.tolist()),
            "action_hold_margin": _summary(action_hold_margin.tolist()),
            "raw_action_probability": _summary(np.maximum(proba[:, 1], proba[:, 2]).tolist()),
            "hold_probability": _summary(proba[:, 0].tolist()),
        },
        "model_format": "ubj",
    }


def build_cost_aware_candidate_specs(
    policies: Sequence[CostAwareLabelPolicyCandidate] | None = None,
    *,
    class_weight_profiles: Sequence[str] | None = None,
    threshold_profiles: Sequence[str] | None = None,
    max_candidates: int | None = None,
) -> list[CostAwareRetrainCandidateSpec]:
    chosen_policies = list(policies or default_cost_aware_label_policy_candidates())
    weights = [str(x) for x in (class_weight_profiles or ["balanced", "buy_sell_boost_light"])]
    thresholds = [str(x) for x in (threshold_profiles or ["balanced", "action_seek_light"])]
    specs: list[CostAwareRetrainCandidateSpec] = []
    for policy in chosen_policies:
        if not bool(policy.approvable):
            continue
        for weight in weights:
            for threshold in thresholds:
                specs.append(CostAwareRetrainCandidateSpec(policy, weight, threshold))
    if max_candidates is not None:
        return specs[: max(1, int(max_candidates))]
    return specs


def select_cost_aware_policies_from_report(report: Mapping[str, Any] | None, *, limit: int = 3) -> list[CostAwareLabelPolicyCandidate]:
    report = dict(report or {})
    policies: list[tuple[float, CostAwareLabelPolicyCandidate]] = []
    for item in report.get("policies") or []:
        if not isinstance(item, Mapping):
            continue
        if item.get("decision") != "PASS":
            continue
        payload = item.get("policy") if isinstance(item.get("policy"), Mapping) else {}
        if not payload:
            continue
        try:
            policy = CostAwareLabelPolicyCandidate(
                name=str(payload.get("name")),
                lookahead=int(payload.get("lookahead")),
                atr_multiplier=float(payload.get("atr_multiplier")),
                cost_bps=float(payload.get("cost_bps", payload.get("round_trip_cost_bps", 0.0))),
                min_edge_bps=float(payload.get("min_edge_bps", 0.0)),
                entry_fee_bps=payload.get("entry_fee_bps"),
                exit_fee_bps=payload.get("exit_fee_bps"),
                entry_slippage_bps=payload.get("entry_slippage_bps"),
                exit_slippage_bps=payload.get("exit_slippage_bps"),
                use_high_low_barriers=bool(payload.get("use_high_low_barriers", True)),
                ambiguous_barrier_policy=str(payload.get("ambiguous_barrier_policy", "hold")),
                approvable=bool(payload.get("approvable", True)),
                family=str(payload.get("family", "cost_aware")),
            )
        except Exception:
            continue
        score = _safe_float(item.get("score"), 0.0)
        policies.append((score, policy))
    policies = sorted(policies, key=lambda pair: pair[0], reverse=True)
    return [policy for _score, policy in policies[: max(1, int(limit))]] or [p for p in default_cost_aware_label_policy_candidates() if p.name == "h30_cost16_edge30_atr3_0"]


def evaluate_sweep_candidate(result: Mapping[str, Any], *, limits: CostAwareRetrainGateLimits | None = None) -> dict[str, Any]:
    gate = evaluate_cost_aware_training_result(result, limits=limits)
    out = dict(result)
    out["candidate_gate"] = gate
    out["decision"] = gate["decision"]
    out["ok"] = gate["ok"]
    out["reason_codes"] = list(gate.get("reason_codes") or [])
    out["warnings"] = list(gate.get("warnings") or [])
    out["score"] = float(gate.get("score", -999.0))
    out["reload_allowed"] = False
    out["approved_for_live_real"] = False
    out["approved_for_paper_candidate"] = False
    return out


def select_best_cost_aware_retrain_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evaluated = [dict(item) for item in candidates]
    if not evaluated:
        return {
            "contract_version": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
            "decision": "BLOCK",
            "approved": False,
            "reason_codes": ["NO_CANDIDATES"],
            "best_candidate": None,
        }
    sorted_items = sorted(evaluated, key=lambda item: _safe_float(item.get("score"), -999.0), reverse=True)
    pass_items = [item for item in sorted_items if item.get("decision") == "PASS"]
    best = pass_items[0] if pass_items else sorted_items[0]
    decision = "PASS" if pass_items else "BLOCK"
    reasons: list[str] = []
    if not pass_items:
        _append_unique(reasons, "NO_COST_AWARE_RETRAIN_CANDIDATE_PASSED")
        for item in sorted_items[:3]:
            for code in item.get("reason_codes") or []:
                _append_unique(reasons, str(code))
    return {
        "contract_version": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
        "decision": decision,
        "approved": decision == "PASS",
        "reason_codes": reasons,
        "best_candidate": best,
    }


def build_cost_aware_retrain_sweep_report(
    candidate_results: Sequence[Mapping[str, Any]],
    *,
    source: str = "unknown",
    promoted_to: str | None = None,
) -> dict[str, Any]:
    candidates = [dict(item) for item in candidate_results]
    selection = select_best_cost_aware_retrain_candidate(candidates)
    decision = str(selection.get("decision") or "BLOCK")
    reasons = list(selection.get("reason_codes") or [])
    return {
        "contract_version": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
        "phase": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
        "report_type": "cost_aware_retrain_sweep_separation_gate",
        "decision": decision,
        "ok": decision == "PASS",
        "source": str(source),
        "candidate_count": len(candidates),
        "approved_for_training_candidate": decision == "PASS",
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "observation_only": True,
        "promoted_to": promoted_to,
        "promotion_performed": bool(promoted_to),
        "reason_codes": reasons,
        "recommendation": (
            "A cost-aware retrain candidate passed the separation gate. Review sidecars and run controlled reload/24E/24F/24C checks; paper/live remain blocked."
            if decision == "PASS"
            else "No cost-aware retrain candidate passed the separation gate. Do not promote/reload; revisit policy, features, or model objective."
        ),
        "selection": selection,
        "candidates": candidates,
        "guardrails": {
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "promotion_requires_explicit_flag": True,
        },
    }
