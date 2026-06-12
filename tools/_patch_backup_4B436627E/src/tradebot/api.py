from __future__ import annotations

import asyncio
from dataclasses import asdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .config import Settings
from .engine import TradeBotEngine
from .persistence import SQLiteStore
from .ai.provider import XGBoostSignalProvider

def train_xgb_model(*args: Any, **kwargs: Any) -> dict[str, Any]:
    # Lazy import keeps lightweight API/status tests from importing XGBoost/Scipy.
    from .training.train_xgb import train

    return train(*args, **kwargs)
from .model_quality_gate import evaluate_training_result_quality
from .observability import normalize_audit_event, summarize_audit_events


class AIReloadPayload(BaseModel):
    model_path: str
    threshold: float | None = None
    buy_threshold: float | None = None
    sell_threshold: float | None = None
    hold_band_low: float | None = None
    hold_band_high: float | None = None
    indecision_margin: float | None = None


class AITrainPayload(BaseModel):
    symbol: str | None = None
    interval: str | None = None
    days: int = Field(default=30, ge=1, le=365)
    out: str | None = None
    base_url: str | None = None
    class_weight_profile: str = 'none'
    threshold_profile: str = 'balanced'
    feature_lag: int | None = None
    reload_after_train: bool = True


def _threshold_payload(settings: Any, payload: AIReloadPayload) -> dict[str, float | None]:
    return {
        'threshold': payload.threshold if payload.threshold is not None else getattr(settings, 'ai_confidence_threshold', 0.60),
        'buy_threshold': payload.buy_threshold if payload.buy_threshold is not None else getattr(settings, 'ai_buy_threshold', 0.64),
        'sell_threshold': payload.sell_threshold if payload.sell_threshold is not None else getattr(settings, 'ai_sell_threshold', 0.57),
        'hold_band_low': payload.hold_band_low if payload.hold_band_low is not None else getattr(settings, 'ai_hold_band_low', 0.45),
        'hold_band_high': payload.hold_band_high if payload.hold_band_high is not None else getattr(settings, 'ai_hold_band_high', 0.55),
        'indecision_margin': payload.indecision_margin if payload.indecision_margin is not None else getattr(settings, 'ai_indecision_margin', 0.08),
    }


def _provider_payload(provider: Any, *, ok: bool, model_path: str, threshold: float) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'ok': bool(ok),
        'reload_ok': bool(ok),
        'model_path': model_path,
        'threshold': float(threshold),
        'available': bool(provider and getattr(provider, 'available', False)),
        'load_error': getattr(provider, 'load_error', None) if provider else None,
    }
    if provider is not None and hasattr(provider, 'schema_info'):
        payload.update(provider.schema_info())
    return payload


def _resolve_training_out(settings: Any, payload: AITrainPayload, symbol: str) -> str:
    raw = payload.out or getattr(settings, 'ai_model_path', '') or f'models/{symbol}_model.ubj'
    path = Path(raw)
    if path.suffix.lower() != '.ubj':
        path = path.with_suffix('.ubj')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.as_posix()


def _clear_runtime_ai_signal_cache(engine: Any, provider: Any) -> None:
    runtime = getattr(engine, 'runtime', None)
    if runtime is None:
        return
    schema_info = provider.schema_info() if provider is not None and hasattr(provider, 'schema_info') else {}
    runtime.last_signal = 'HOLD'
    runtime.signal_reason = 'AI model reloaded; waiting next evaluation'
    runtime.trend = 'UNKNOWN'
    runtime.last_signal_provider = getattr(engine.settings, 'ai_provider_mode', 'local_xgboost')
    runtime.last_signal_confidence = None
    runtime.last_signal_metrics = {
        'schemaValidated': bool(schema_info.get('schema_validated')),
        'schemaVersion': schema_info.get('schema_version'),
        'featurePackName': schema_info.get('feature_pack_name'),
        'featureCount': schema_info.get('feature_count'),
        'featureLag': schema_info.get('feature_lag'),
        'loadError': schema_info.get('load_error'),
        'reloadClearedStaleSignal': True,
    }
    runtime.last_evaluated_close_time = None
    runtime.last_signal_key = None
    save = getattr(engine, '_save_runtime', None)
    if callable(save):
        try:
            save()
        except Exception:
            pass



def _safe_engine_log(engine: Any, level: str, code: str, message: str, data: dict[str, Any] | None = None) -> None:
    logger = getattr(engine, 'logger', None)
    fn = getattr(logger, level, None) if logger is not None else None
    if callable(fn):
        try:
            fn(code, message, data or {})
        except Exception:
            pass


def _fetch_audit_events_from_store(store: Any, *, limit: int = 200, order: str = 'desc', category: str | None = None, severity: str | None = None, code_prefix: str | None = None, since_ts: int | None = None) -> list[dict[str, Any]]:
    fetch_audit = getattr(store, 'fetch_audit_events', None)
    if callable(fetch_audit):
        return fetch_audit(limit=limit, order=order, category=category, severity=severity, code_prefix=code_prefix, since_ts=since_ts)
    fetch_logs = getattr(store, 'fetch_logs', None)
    if not callable(fetch_logs):
        return []
    try:
        raw = fetch_logs(limit=0, order=order)
    except TypeError:
        raw = fetch_logs(limit=limit)
        if order.lower() == 'desc':
            raw = list(reversed(list(raw)))
    events = [normalize_audit_event(dict(item)) for item in list(raw)]
    category_q = str(category or '').strip().lower()
    severity_q = str(severity or '').strip().lower()
    code_q = str(code_prefix or '').strip().upper()
    filtered: list[dict[str, Any]] = []
    for event in events:
        if since_ts is not None and int(event.get('ts') or 0) < int(since_ts):
            continue
        if category_q and str(event.get('category') or '').lower() != category_q:
            continue
        if severity_q and str(event.get('severity') or '').lower() != severity_q:
            continue
        if code_q and not str(event.get('code') or '').upper().startswith(code_q):
            continue
        filtered.append(event)
    return filtered[:limit] if limit > 0 else filtered



def _bootstrap_error(app: FastAPI) -> str | None:
    error = getattr(app.state, 'bootstrap_error', None)
    if error is None:
        return None
    error_text = str(error).strip()
    return error_text or None


def _build_health_payload(app: FastAPI, engine: Any) -> dict[str, Any]:
    error = _bootstrap_error(app)
    degraded = error is not None
    running = False if degraded else bool(getattr(engine, '_running', False))
    return {
        'ok': not degraded,
        'degraded': degraded,
        'running': running,
        'engine_running': running,
        'symbol': getattr(getattr(engine, 'settings', None), 'symbol', None),
        'bootstrap_ok': not degraded,
        'bootstrap_error': error,
        'start_error': error,
    }


def _build_degraded_status_payload(app: FastAPI, engine: Any) -> dict[str, Any]:
    error = _bootstrap_error(app)
    return {
        'ok': False,
        'degraded': True,
        'state': 'STOPPED',
        'symbol': getattr(getattr(engine, 'settings', None), 'symbol', None),
        'running': False,
        'engine_running': False,
        'bootstrap_ok': False,
        'bootstrap_error': error,
        'start_error': error,
    }

def create_app(engine: TradeBotEngine) -> FastAPI:
    app = FastAPI(title="Trade Bot Python API", version="0.2.6")

    @app.get('/health')
    async def health() -> dict:
        return _build_health_payload(app, engine)

    @app.get('/status')
    async def status() -> dict:
        if _bootstrap_error(app) is not None:
            return _build_degraded_status_payload(app, engine)
        payload = await engine.get_status()
        if isinstance(payload, dict):
            payload.setdefault('ok', True)
            payload.setdefault('degraded', False)
            payload.setdefault('bootstrap_ok', True)
            payload.setdefault('bootstrap_error', None)
            payload.setdefault('start_error', None)
        return payload

    @app.get('/settings')
    async def settings() -> dict:
        return engine.settings.to_dict() if hasattr(engine.settings, 'to_dict') else {}

    @app.get('/ai/config')
    async def ai_config() -> dict:
        provider = getattr(engine, 'ai_provider', None)
        payload = {
            'enabled': engine.settings.ai_provider_enabled,
            'mode': engine.settings.ai_provider_mode,
            'model_path': engine.settings.ai_model_path,
            'threshold': engine.settings.ai_confidence_threshold,
            'available': bool(provider and getattr(provider, 'available', False)),
            'load_error': getattr(provider, 'load_error', None) if provider else None,
        }
        if provider is not None and hasattr(provider, 'schema_info'):
            payload.update(provider.schema_info())
        return payload

    def _reload_ai_provider(payload: AIReloadPayload) -> dict[str, Any]:
        thresholds = _threshold_payload(engine.settings, payload)
        _safe_engine_log(engine, 'info', 'AI_RELOAD_REQUESTED', 'AI model reload talebi alındı', {'model_path': payload.model_path})
        provider = getattr(engine, 'ai_provider', None)
        model_path = payload.model_path
        if provider is None and engine.settings.ai_provider_enabled and engine.settings.ai_provider_mode == 'local_xgboost':
            provider = XGBoostSignalProvider(model_path, threshold=float(thresholds['threshold'] or 0.60))
            reload_ok = bool(getattr(provider, 'available', False))
            if reload_ok:
                engine.ai_provider = provider
        elif provider is not None and hasattr(provider, 'reload'):
            result = provider.reload(model_path=model_path, **thresholds)
            reload_ok = bool(result) if isinstance(result, bool) else bool(getattr(provider, 'available', False))
        else:
            reload_ok = False

        if reload_ok:
            engine.settings.ai_model_path = model_path
            engine.settings.ai_confidence_threshold = float(thresholds['threshold'] or 0.60)
            engine.settings.ai_buy_threshold = float(thresholds['buy_threshold'] or 0.64)
            engine.settings.ai_sell_threshold = float(thresholds['sell_threshold'] or 0.57)
            engine.settings.ai_hold_band_low = float(thresholds['hold_band_low'] or 0.45)
            engine.settings.ai_hold_band_high = float(thresholds['hold_band_high'] or 0.55)
            engine.settings.ai_indecision_margin = float(thresholds['indecision_margin'] or 0.08)
            _clear_runtime_ai_signal_cache(engine, provider)

        result_payload = _provider_payload(provider, ok=reload_ok, model_path=model_path, threshold=float(thresholds['threshold'] or 0.60))
        if reload_ok:
            _safe_engine_log(engine, 'info', 'AI_RELOAD_SUCCEEDED', 'AI model reload başarılı', result_payload)
        else:
            _safe_engine_log(engine, 'warn', 'AI_RELOAD_FAILED', 'AI model reload başarısız', result_payload)
        return result_payload

    @app.post('/ai/reload')
    async def ai_reload(payload: AIReloadPayload) -> dict:
        return _reload_ai_provider(payload)

    @app.post('/ai/train')
    async def ai_train(payload: AITrainPayload) -> dict:
        symbol = (payload.symbol or engine.settings.symbol).upper()
        interval = payload.interval or engine.settings.kline_interval
        base_url = payload.base_url or engine.settings.base_url
        out = _resolve_training_out(engine.settings, payload, symbol)
        _safe_engine_log(engine, 'info', 'AI_TRAIN_REQUESTED', 'AI model eğitimi başlatıldı', {'symbol': symbol, 'interval': interval, 'days': int(payload.days), 'out': out, 'reload_after_train': payload.reload_after_train})
        try:
            result = await asyncio.to_thread(
            train_xgb_model,
            symbol,
            interval,
            int(payload.days),
            out,
            base_url,
            class_weight_profile=payload.class_weight_profile,
            threshold_profile=payload.threshold_profile,
                feature_lag=payload.feature_lag,
            )
        except Exception as exc:
            _safe_engine_log(engine, 'error', 'AI_TRAIN_FAILED', 'AI model eğitimi başarısız', {'symbol': symbol, 'interval': interval, 'days': int(payload.days), 'out': out, 'error': str(exc)})
            raise
        quality_gate = evaluate_training_result_quality(result, settings=engine.settings)
        _safe_engine_log(engine, 'info', 'AI_TRAIN_SUCCEEDED', 'AI model eğitimi tamamlandı', {'symbol': symbol, 'interval': interval, 'days': int(payload.days), 'model_path': result.get('model_path') or result.get('output'), 'samples': result.get('samples'), 'clean_samples': result.get('clean_samples'), 'feature_schema_version': result.get('feature_schema_version'), 'quality_gate_decision': quality_gate.get('decision'), 'quality_gate_reasons': quality_gate.get('reason_codes')})
        response: dict[str, Any] = {'ok': True, 'trained': True, 'training': result, 'quality_gate': quality_gate, 'reloaded': False, 'reload_blocked': False}
        if payload.reload_after_train:
            if not bool(quality_gate.get('reload_allowed')):
                response['ok'] = False
                response['reload_blocked'] = True
                _safe_engine_log(engine, 'warn', 'AI_RELOAD_BLOCKED_MODEL_QUALITY_GATE', 'Eğitilen model kalite kapısından geçemedi; reload engellendi', {'symbol': symbol, 'interval': interval, 'model_path': result.get('model_path') or result.get('output') or out, 'quality_gate': quality_gate})
                return response
            reload_payload = AIReloadPayload(
                model_path=result.get('model_path') or result.get('output') or out,
                threshold=getattr(engine.settings, 'ai_confidence_threshold', 0.60),
            )
            reload_result = _reload_ai_provider(reload_payload)
            response['reloaded'] = bool(reload_result.get('reload_ok'))
            response['ai'] = reload_result
            response['ok'] = bool(reload_result.get('reload_ok'))
        return response

    @app.get('/logs')
    async def logs(limit: int = 200, order: str = 'desc') -> list[dict]:
        normalized_order = 'asc' if order.lower() == 'asc' else 'desc'
        normalized_limit = max(limit, 0)
        try:
            return engine.store.fetch_logs(limit=normalized_limit, order=normalized_order)
        except TypeError:
            logs_out = engine.store.fetch_logs(limit=normalized_limit)
            if normalized_order == 'asc':
                return list(logs_out)
            return list(reversed(list(logs_out)))



    @app.get('/events/audit')
    async def audit_events(
        limit: int = 200,
        order: str = 'desc',
        category: str | None = None,
        severity: str | None = None,
        code_prefix: str | None = None,
        since_ts: int | None = None,
    ) -> dict[str, Any]:
        normalized_order = 'asc' if order.lower() == 'asc' else 'desc'
        normalized_limit = max(limit, 0)
        events = _fetch_audit_events_from_store(
            engine.store,
            limit=normalized_limit,
            order=normalized_order,
            category=category,
            severity=severity,
            code_prefix=code_prefix,
            since_ts=since_ts,
        )
        return {
            'ok': True,
            'contract_version': '4B.4.3.6.6.11',
            'order': normalized_order,
            'limit': normalized_limit,
            'filters': {
                'category': category,
                'severity': severity,
                'code_prefix': code_prefix,
                'since_ts': since_ts,
            },
            'count': len(events),
            'summary': summarize_audit_events(events),
            'events': events,
        }

    @app.get('/market/klines')
    async def market_klines(symbol: str | None = None, interval: str | None = None, limit: int = 120) -> list[dict]:
        candles = await engine.exchange.fetch_klines(symbol=symbol or engine.settings.symbol, interval=interval or engine.settings.kline_interval, limit=max(1, min(limit, 500)))
        return [asdict(candle) if not isinstance(candle, dict) else candle for candle in candles]

    @app.post('/start')
    async def start() -> dict:
        result = await engine.start()
        started = bool(result)
        return {'ok': True, 'started': started, 'already_running': not started}

    @app.post('/stop')
    async def stop() -> dict:
        result = await engine.stop()
        stopped = bool(result)
        return {'ok': True, 'stopped': stopped, 'already_stopped': not stopped}

    @app.post('/force-buy')
    async def force_buy() -> dict:
        _safe_engine_log(engine, 'info', 'OPERATOR_ACTION_REQUESTED', 'Operatör aksiyonu alındı', {'action': 'force_buy', 'symbol': engine.settings.symbol})
        await engine.force_buy()
        _safe_engine_log(engine, 'info', 'OPERATOR_ACTION_COMPLETED', 'Operatör aksiyonu tamamlandı', {'action': 'force_buy', 'symbol': engine.settings.symbol})
        return {'ok': True}

    @app.post('/force-sell')
    async def force_sell() -> dict:
        _safe_engine_log(engine, 'info', 'OPERATOR_ACTION_REQUESTED', 'Operatör aksiyonu alındı', {'action': 'force_sell', 'symbol': engine.settings.symbol})
        await engine.force_sell()
        _safe_engine_log(engine, 'info', 'OPERATOR_ACTION_COMPLETED', 'Operatör aksiyonu tamamlandı', {'action': 'force_sell', 'symbol': engine.settings.symbol})
        return {'ok': True}

    @app.post('/cancel-pending')
    async def cancel_pending() -> dict:
        _safe_engine_log(engine, 'info', 'OPERATOR_ACTION_REQUESTED', 'Operatör aksiyonu alındı', {'action': 'cancel_pending', 'symbol': engine.settings.symbol})
        await engine.cancel_pending()
        _safe_engine_log(engine, 'info', 'OPERATOR_ACTION_COMPLETED', 'Operatör aksiyonu tamamlandı', {'action': 'cancel_pending', 'symbol': engine.settings.symbol})
        return {'ok': True}

    @app.post('/balance-sync')
    async def balance_sync() -> dict:
        await engine.sync_balances()
        return {'ok': True}

    @app.post('/risk-reset')
    async def risk_reset() -> dict:
        await engine.risk_reset()
        return {'ok': True}

    @app.post('/safe-mode/toggle')
    async def toggle_safe_mode() -> dict:
        await engine.toggle_safe_mode()
        return {'ok': True}

    return app


def create_managed_app(settings: Settings) -> FastAPI:
    store = SQLiteStore(settings.database_path)
    engine = TradeBotEngine(settings, store)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.bootstrap_error = None
        try:
            await engine.start()
        except Exception as exc:
            app.state.bootstrap_error = str(exc)
            try:
                setattr(engine, '_running', False)
            except Exception:
                pass
        try:
            yield
        finally:
            try:
                await engine.close()
            except Exception:
                pass

    app = create_app(engine)
    app.router.lifespan_context = lifespan
    return app
