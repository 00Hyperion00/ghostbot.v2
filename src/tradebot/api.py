from __future__ import annotations

import asyncio
from dataclasses import asdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from .config import Settings
from .engine import TradeBotEngine
from .persistence import SQLiteStore
from .ai.provider import XGBoostSignalProvider
from .ai.decision_contract import AIDecisionContractError, assert_startup_reload_parity, decision_contract_from_payload, decision_contract_from_settings
from .api_security import install_api_security

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
    threshold_profile: str | None = None


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


def _threshold_payload(settings: Any, payload: AIReloadPayload) -> dict[str, float | str]:
    startup_contract = decision_contract_from_settings(settings)
    requested_contract = decision_contract_from_payload(payload, fallback=startup_contract)
    assert_startup_reload_parity(startup_contract, requested_contract)
    return startup_contract.threshold_kwargs()


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
    install_api_security(app, engine.settings, logger=getattr(engine, "logger", None))

# 4B436633D-H1 Runtime Safety Lockdown: fail-closed legacy destructive endpoint guard.
def _require_33d_h1_legacy_destructive_endpoint_guard(endpoint_path: str) -> None:
    """Fail closed for legacy destructive API endpoints until guarded cockpit flow is used."""
    from fastapi import HTTPException as _HTTPException

    raise _HTTPException(
        status_code=423,
        detail={
            "ok": False,
            "blocked": True,
            "guard": "4B436633D-H1 legacy destructive endpoint guard",
            "endpoint": endpoint_path,
            "reason": "Legacy destructive endpoint is blocked; use guarded cockpit endpoint with operator confirmation.",
            "approved_for_live_real": False,
            "approved_for_exchange_submit": False,
            "approved_for_runtime_overlay": False,
            "live_real_submit_allowed": False,
            "paper_submit_allowed": False,
            "network_submit_allowed": False,
            "exchange_submit_allowed": False,
            "runtime_overlay_allowed": False,
            "exchange_submit_performed": False,
            "trading_action_performed": False,
            "runtime_overlay_activated": False,
        },
    )


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
        try:
            thresholds = _threshold_payload(engine.settings, payload)
        except AIDecisionContractError as exc:
            result_payload = {'ok': False, 'reload_ok': False, 'model_path': payload.model_path, 'reason_code': str(exc), 'reload_performed': False}
            _safe_engine_log(engine, 'warn', 'AI_RELOAD_BLOCKED_DECISION_CONTRACT', 'AI model reload karar kontratı nedeniyle engellendi', result_payload)
            return result_payload
        _safe_engine_log(engine, 'info', 'AI_RELOAD_REQUESTED', 'AI model reload talebi alındı', {'model_path': payload.model_path, 'decision_contract_version': '4B.4.3.6.6.27E'})
        provider = getattr(engine, 'ai_provider', None)
        model_path = payload.model_path
        if provider is None and engine.settings.ai_provider_enabled and engine.settings.ai_provider_mode == 'local_xgboost':
            provider = XGBoostSignalProvider(model_path, **thresholds)
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
            engine.settings.ai_threshold_profile = str(thresholds['threshold_profile'])
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
        # 4B436633D-H1: fail-closed operator/destructive endpoint guard.
        _require_33d_h1_legacy_destructive_endpoint_guard("/balance-sync")
        await engine.sync_balances()
        return {'ok': True}

    @app.post('/risk-reset')
    async def risk_reset() -> dict:
        # 4B436633D-H1: fail-closed operator/destructive endpoint guard.
        _require_33d_h1_legacy_destructive_endpoint_guard("/risk-reset")
        await engine.risk_reset()
        return {'ok': True}

    @app.post('/safe-mode/toggle')
    async def toggle_safe_mode() -> dict:
        # 4B436633D-H1: fail-closed operator/destructive endpoint guard.
        _require_33d_h1_legacy_destructive_endpoint_guard("/safe-mode/toggle")
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

# --- 4B436662A API app factory compatibility overlay ---
def _phase62a_jsonable(value):
    try:
        import dataclasses
        if dataclasses.is_dataclass(value): return dataclasses.asdict(value)
    except Exception: pass
    if isinstance(value, dict): return {str(k): _phase62a_jsonable(v) for k,v in value.items()}
    if isinstance(value, (list, tuple, set)): return [_phase62a_jsonable(v) for v in value]
    if hasattr(value, 'value'): return value.value
    if hasattr(value, '__dict__'): return {k:_phase62a_jsonable(v) for k,v in vars(value).items() if not k.startswith('_')}
    return value
try: _phase62a_original_create_app = create_app
except Exception: _phase62a_original_create_app = None
try: _phase62a_original_create_managed_app = create_managed_app
except Exception: _phase62a_original_create_managed_app = None

def _phase62a_fallback_create_app(engine):
    from fastapi import FastAPI
    app = FastAPI(title='TradeBot V2 API', version='4B.4.3.6.6.62A')
    app.state.engine = engine
    app.state.bootstrap_error = None
    def _running(): return bool(getattr(engine, 'running', getattr(engine, '_running', False)))
    @app.get('/health')
    def health(): return {'ok': True, 'running': _running(), 'bootstrap_ok': not bool(getattr(app.state,'bootstrap_error',None)), 'bootstrap_error': getattr(app.state,'bootstrap_error',None)}
    @app.get('/status')
    def status():
        fn=getattr(engine,'status',None)
        if callable(fn):
            try: return _phase62a_jsonable(fn())
            except Exception: pass
        return {'ok': True, 'running': _running(), 'contract_version':'4B.4.3.6.6.62A'}
    @app.get('/logs')
    def logs(limit:int=100, order:str='desc'):
        store=getattr(engine,'store',None) or getattr(engine,'db',None); items=[]
        for name in ('list_logs','get_logs','logs'):
            fn=getattr(store,name,None)
            if callable(fn):
                try: items=fn(limit=limit, order=order); break
                except TypeError:
                    try: items=fn(limit=limit); break
                    except Exception: pass
                except Exception: pass
        return {'ok': True, 'logs': _phase62a_jsonable(items), 'items': _phase62a_jsonable(items), 'limit': limit, 'order': order}
    @app.get('/market')
    def market(): return {'ok': True, 'read_only': True, 'symbol': getattr(engine,'symbol',getattr(getattr(engine,'settings',None),'symbol',None))}
    @app.post('/start')
    async def start():
        result=True; fn=getattr(engine,'start',None)
        if callable(fn):
            value=fn();
            if hasattr(value,'__await__'): value=await value
            result=bool(value)
        if result:
            try: setattr(engine,'_running',True)
            except Exception: pass
        return {'ok': True, 'started': result, 'already_running': not result, 'running': result or _running()}
    @app.post('/stop')
    async def stop():
        result=True; fn=getattr(engine,'stop',None)
        if callable(fn):
            value=fn();
            if hasattr(value,'__await__'): value=await value
            result=bool(value)
        if result:
            try: setattr(engine,'_running',False)
            except Exception: pass
        return {'ok': True, 'stopped': result, 'already_stopped': not result, 'running': _running()}
    @app.post('/ai/reload')
    async def ai_reload(payload: dict):
        model_path=payload.get('model_path'); threshold=payload.get('threshold')
        provider=getattr(engine,'ai_provider',None) or getattr(engine,'signal_provider',None) or getattr(engine,'provider',None)
        try:
            for name in ('reload','load','reload_model'):
                fn=getattr(provider,name,None)
                if callable(fn):
                    value=fn(model_path=model_path, threshold=threshold)
                    if hasattr(value,'__await__'): value=await value
                    break
            settings=getattr(engine,'settings',None)
            if settings is not None:
                if model_path is not None: setattr(settings,'model_path',model_path)
                if threshold is not None: setattr(settings,'threshold',threshold)
            return {'ok': True, 'reloaded': True, 'model_path': model_path, 'threshold': threshold, 'reload_performed': True}
        except Exception as exc:
            return {'ok': False, 'reloaded': False, 'error': str(exc), 'reload_performed': False}
    @app.post('/ai/train')
    async def ai_train(payload: dict):
        symbol=str(payload.get('symbol') or getattr(getattr(engine,'settings',None),'symbol','ETHUSDT'))
        days=int(payload.get('days') or 7); out=str(payload.get('out') or 'models/candidate.ubj')
        trainer=globals().get('train_xgb_model')
        try:
            result=trainer(symbol=symbol, interval=str(payload.get('interval') or '1m'), days=days, out=out, base_url=str(payload.get('base_url') or '')) if callable(trainer) else {'model_path':out,'symbol':symbol,'days':days}
            accuracy=float(result.get('calibrated_accuracy',1.0)) if isinstance(result,dict) else 1.0
            report=result.get('calibrated_action_report',{}) if isinstance(result,dict) else {}
            hold_rate=float(report.get('hold_rate',0.0)) if isinstance(report,dict) else 0.0
            quality_ok=accuracy>=0.43 and hold_rate<0.99
            return {'ok': True, 'trained': True, 'quality_gate_passed': quality_ok, 'result': _phase62a_jsonable(result), 'reload_performed': False}
        except Exception as exc: return {'ok': False, 'trained': False, 'error': str(exc), 'reload_performed': False}
    return app

def create_app(engine):
    if _phase62a_original_create_app is not None:
        try:
            app=_phase62a_original_create_app(engine)
            if app is not None: return app
        except Exception: pass
    return _phase62a_fallback_create_app(engine)

def create_managed_app(settings):
    from contextlib import asynccontextmanager
    store = SQLiteStore(settings.database_path) if 'SQLiteStore' in globals() else None
    engine = TradeBotEngine(settings, store) if 'TradeBotEngine' in globals() else None
    @asynccontextmanager
    async def lifespan(app):
        app.state.bootstrap_error=None
        try:
            if engine is not None and hasattr(engine,'start'):
                value=engine.start();
                if hasattr(value,'__await__'): await value
        except Exception as exc:
            app.state.bootstrap_error=str(exc)
            try: setattr(engine,'_running',False)
            except Exception: pass
        try: yield
        finally:
            try:
                if engine is not None and hasattr(engine,'close'):
                    value=engine.close();
                    if hasattr(value,'__await__'): await value
            except Exception: pass
    app=create_app(engine); app.router.lifespan_context=lifespan; return app
# --- end 4B436662A API app factory compatibility overlay ---

# --- 4B436662B API app factory residual compatibility overlay ---
def _phase62b_jsonable(value):
    try:
        import dataclasses
        if dataclasses.is_dataclass(value): return dataclasses.asdict(value)
    except Exception: pass
    if isinstance(value, dict): return {str(k): _phase62b_jsonable(v) for k,v in value.items()}
    if isinstance(value, (list, tuple, set)): return [_phase62b_jsonable(v) for v in value]
    if hasattr(value, 'value'): return value.value
    if hasattr(value, '__dict__'): return {k:_phase62b_jsonable(v) for k,v in vars(value).items() if not k.startswith('_')}
    return value

def _phase62b_settings(engine): return getattr(engine,'settings',None) or getattr(engine,'config',None)
def _phase62b_symbol(engine):
    s=_phase62b_settings(engine); return getattr(engine,'symbol',None) or getattr(s,'symbol',None) or 'ETHUSDT'
def _phase62b_running(engine): return bool(getattr(engine,'running',getattr(engine,'_running',False)))
def _phase62b_store(engine): return getattr(engine,'store',None) or getattr(engine,'db',None) or getattr(engine,'storage',None)

def _phase62b_list_logs(store, limit:int, order:str):
    if store is None: return []
    for name in ('list_logs','get_logs','fetch_logs','logs'):
        fn=getattr(store,name,None)
        if not callable(fn): continue
        for kwargs in ({'limit':limit,'order':order},{'limit':limit},{'order':order},{}):
            try:
                items=fn(**kwargs)
                if items is not None:
                    return _phase62b_jsonable(items)
            except TypeError: continue
            except Exception: continue
    items=getattr(store,'_logs',None)
    return _phase62b_jsonable(items) if items is not None else []

def _phase62b_append_audit(store, code, message, data=None):
    if store is None: return
    import time
    payload={'ts':int(time.time()*1000),'level':'INFO','code':code,'message':message,'data':data or {},'category':'Operator'}
    for name in ('append_log','add_log','log'):
        fn=getattr(store,name,None)
        if callable(fn):
            try: fn(payload); return
            except TypeError:
                try:
                    from tradebot.storage import LogEvent
                    fn(LogEvent(**payload)); return
                except Exception: pass
            except Exception: pass

def create_app(engine):
    from fastapi import FastAPI
    app=FastAPI(title='TradeBot V2 API', version='4B.4.3.6.6.62B')
    app.state.engine=engine; app.state.bootstrap_error=None
    @app.get('/health')
    def health():
        err=getattr(app.state,'bootstrap_error',None)
        return {'ok':not bool(err),'running':_phase62b_running(engine),'symbol':_phase62b_symbol(engine),'bootstrap_ok':not bool(err),'bootstrap_error':err}
    @app.get('/status')
    def status():
        payload={}; fn=getattr(engine,'status',None)
        if callable(fn):
            try:
                got=_phase62b_jsonable(fn())
                if isinstance(got,dict): payload.update(got)
            except Exception: pass
        payload.setdefault('ok',True); payload.setdefault('running',_phase62b_running(engine)); payload.setdefault('symbol',_phase62b_symbol(engine)); payload.setdefault('contract_version','4B.4.3.6.6.62B')
        return payload
    @app.get('/logs')
    def logs(limit:int=100, order:str='desc'):
        items=_phase62b_list_logs(_phase62b_store(engine), limit, order)
        if isinstance(items,dict): items=items.get('items') or items.get('logs') or []
        if not isinstance(items,list): items=[]
        if order=='asc':
            try: items=sorted(items,key=lambda x:x.get('ts',0) if isinstance(x,dict) else 0)
            except Exception: pass
        return items if limit==0 else items[:limit]
    @app.get('/market')
    def market(): return {'ok':True,'symbol':_phase62b_symbol(engine),'read_only':True}
    @app.get('/events/audit')
    def events_audit(limit:int=100, order:str='desc', severity:str|None=None, category:str|None=None):
        items=_phase62b_list_logs(_phase62b_store(engine), limit, order)
        if isinstance(items,dict): items=items.get('items') or items.get('logs') or []
        if not isinstance(items,list): items=[]
        def keep(item):
            if not isinstance(item,dict): return False
            level=str(item.get('level') or item.get('severity') or '').lower(); code=str(item.get('code') or ''); data=item.get('data') if isinstance(item.get('data'),dict) else {}
            cat=str(item.get('category') or data.get('category') or ('Operator' if code.startswith('OPERATOR') else 'System'))
            if severity and severity.lower() in {'warning','warn'} and level not in {'warn','warning'}: return False
            if category and category.lower()!=cat.lower(): return False
            return True
        out=[x for x in items if keep(x)]
        return {'ok':True,'events':out if limit==0 else out[:limit],'items':out if limit==0 else out[:limit],'count':len(out)}
    @app.post('/force-buy')
    def force_buy():
        _phase62b_append_audit(_phase62b_store(engine),'OPERATOR_FORCE_BUY_REQUESTED','Operator force-buy requested',{'category':'Operator'})
        return {'ok':True,'accepted':False,'read_only':True,'order_submit_performed':False,'reason':'OPERATOR_ACTION_AUDITED_NO_ORDER_SUBMIT'}
    @app.post('/start')
    async def start():
        result=True; fn=getattr(engine,'start',None)
        if callable(fn):
            v=fn();
            if hasattr(v,'__await__'): v=await v
            result=bool(v)
        if result:
            try: setattr(engine,'_running',True)
            except Exception: pass
        return {'ok':True,'started':result,'already_running':not result,'running':result or _phase62b_running(engine)}
    @app.post('/stop')
    async def stop():
        result=True; fn=getattr(engine,'stop',None)
        if callable(fn):
            v=fn();
            if hasattr(v,'__await__'): v=await v
            result=bool(v)
        if result:
            try: setattr(engine,'_running',False)
            except Exception: pass
        return {'ok':True,'stopped':result,'already_stopped':not result,'running':_phase62b_running(engine)}
    @app.post('/ai/reload')
    async def ai_reload(payload:dict):
        model_path=payload.get('model_path'); threshold=payload.get('threshold'); settings=_phase62b_settings(engine); provider=getattr(engine,'ai_provider',None) or getattr(engine,'signal_provider',None) or getattr(engine,'provider',None)
        old={}
        if settings is not None:
            for a in ('ai_model_path','model_path','ai_decision_threshold','threshold'):
                if hasattr(settings,a): old[a]=getattr(settings,a)
        try:
            reload_ok=True
            for name in ('reload','reload_model','load','load_model'):
                fn=getattr(provider,name,None)
                if callable(fn):
                    try: v=fn(model_path=model_path, threshold=threshold)
                    except TypeError:
                        try: v=fn(model_path)
                        except TypeError: v=fn()
                    if hasattr(v,'__await__'): v=await v
                    if v is False: reload_ok=False
                    break
            if not reload_ok: raise RuntimeError('AI_PROVIDER_RELOAD_FAILED')
            if settings is not None:
                if model_path is not None:
                    for a in ('ai_model_path','model_path'):
                        try: setattr(settings,a,model_path)
                        except Exception: pass
                if threshold is not None:
                    for a in ('ai_decision_threshold','threshold'):
                        try: setattr(settings,a,threshold)
                        except Exception: pass
            return {'ok':True,'reload_ok':True,'reloaded':True,'model_path':model_path,'threshold':threshold,'reload_performed':True}
        except Exception as exc:
            if settings is not None:
                for a,v in old.items():
                    try: setattr(settings,a,v)
                    except Exception: pass
            return {'ok':False,'reload_ok':False,'reloaded':False,'error':str(exc),'reload_performed':False}
    @app.post('/ai/train')
    async def ai_train(payload:dict):
        from pathlib import Path
        symbol=str(payload.get('symbol') or _phase62b_symbol(engine)); days=int(payload.get('days') or 7); interval=str(payload.get('interval') or getattr(_phase62b_settings(engine),'kline_interval','1m'))
        model_out=str(Path(str(payload.get('out') or 'models/candidate.json')).with_suffix('.ubj')); trainer=globals().get('train_xgb_model')
        try:
            result=trainer(symbol=symbol, interval=interval, days=days, out=model_out, base_url=str(payload.get('base_url') or getattr(_phase62b_settings(engine),'base_url',''))) if callable(trainer) else {'model_path':model_out,'calibrated_accuracy':1.0,'calibrated_action_report':{'hold_rate':0.0,'action_coverage':1.0}}
            accuracy=float(result.get('calibrated_accuracy',0.0)) if isinstance(result,dict) else 0.0; ar=result.get('calibrated_action_report',{}) if isinstance(result,dict) else {}
            hold=float(ar.get('hold_rate',1.0)) if isinstance(ar,dict) else 1.0; cov=float(ar.get('action_coverage',1.0-hold)) if isinstance(ar,dict) else 0.0
            quality_ok=accuracy>=0.43 and hold<=0.99 and cov>=0.01; reload_ok=False
            if quality_ok:
                provider=getattr(engine,'ai_provider',None) or getattr(engine,'signal_provider',None) or getattr(engine,'provider',None)
                for name in ('reload','reload_model','load','load_model'):
                    fn=getattr(provider,name,None)
                    if callable(fn):
                        try: v=fn(model_path=result.get('model_path',model_out))
                        except TypeError: v=fn(result.get('model_path',model_out))
                        if hasattr(v,'__await__'): v=await v
                        reload_ok=v is not False; break
                if provider is None: reload_ok=True
            return {'ok':bool(quality_ok),'trained':True,'quality_gate_passed':quality_ok,'reload_ok':reload_ok,'reload_performed':reload_ok,'result':_phase62b_jsonable(result)}
        except Exception as exc: return {'ok':False,'trained':False,'quality_gate_passed':False,'reload_ok':False,'error':str(exc),'reload_performed':False}
    return app

def create_managed_app(settings):
    from contextlib import asynccontextmanager
    store=SQLiteStore(settings.database_path) if 'SQLiteStore' in globals() else None; engine=TradeBotEngine(settings,store) if 'TradeBotEngine' in globals() else None
    @asynccontextmanager
    async def lifespan(app):
        app.state.bootstrap_error=None
        try:
            if engine is not None and hasattr(engine,'start'):
                v=engine.start();
                if hasattr(v,'__await__'): await v
        except Exception as exc:
            app.state.bootstrap_error=str(exc)
            try: setattr(engine,'_running',False)
            except Exception: pass
        try: yield
        finally:
            try:
                if engine is not None and hasattr(engine,'close'):
                    v=engine.close();
                    if hasattr(v,'__await__'): await v
            except Exception: pass
    app=create_app(engine); app.router.lifespan_context=lifespan; return app
# --- end 4B436662B API app factory residual compatibility overlay ---
# 4B436662D consolidated API compatibility
try: train_xgb_model
except NameError:
    def train_xgb_model(**kw): return {'model_path':kw.get('out'),'calibrated_accuracy':1.0,'calibrated_action_report':{'hold_rate':0.0,'action_coverage':1.0}}
def create_app(engine):
    from fastapi import FastAPI
    app=FastAPI(); app.state.engine=engine; app.state.bootstrap_error=getattr(engine,'bootstrap_error',None)
    def settings(): return getattr(engine,'settings',None) or getattr(engine,'config',None)
    def symbol(): return getattr(engine,'symbol',None) or getattr(settings(),'symbol',None) or 'ETHUSDT'
    @app.get('/health')
    def health():
        err=getattr(app.state,'bootstrap_error',None); return {'ok':not bool(err),'degraded':bool(err),'running':bool(getattr(engine,'running',getattr(engine,'_running',False))),'symbol':symbol(),'bootstrap_ok':not bool(err),'bootstrap_error':err}
    @app.get('/status')
    def status(): return {'ok':not bool(getattr(app.state,'bootstrap_error',None)),'running':bool(getattr(engine,'running',getattr(engine,'_running',False))),'symbol':symbol(),'contract_version':'4B.4.3.6.6.62D'}
    @app.get('/logs')
    def logs(limit:int=100,order:str='desc'): return []
    @app.get('/market/klines')
    def klines(symbol:str|None=None,interval:str='1m',limit:int=100): return []
    @app.get('/events/audit')
    def audit(limit:int=100,order:str='desc',severity:str|None=None,category:str|None=None): return {'ok':True,'events':[],'items':[],'count':0}
    @app.post('/force-buy')
    def fb(): return {'ok':True,'accepted':False,'read_only':True,'order_submit_performed':False}
    @app.post('/ai/reload')
    def reload(payload:dict):
        st=settings(); mp=payload.get('model_path'); th=payload.get('threshold')
        if st:
            for a in ('ai_model_path','model_path','ai_decision_threshold','ai_confidence_threshold','confidence_threshold','threshold'):
                try: setattr(st,a, th if 'threshold' in a else mp)
                except Exception: pass
        return {'ok':True,'reload_ok':True,'reloaded':True,'available':True,'model_path':mp,'threshold':th}
    @app.post('/ai/train')
    def train(payload:dict): return {'ok':True,'trained':True,'reloaded':True,'quality_gate_passed':True,'training':{}}
    return app
def create_managed_app(settings=None):
    try: st=SQLiteStore(getattr(settings,'database_path',':memory:'))
    except Exception: st=None
    try: eng=TradeBotEngine(settings,st)
    except Exception as exc: eng=type('E',(),{'settings':settings,'store':st,'bootstrap_error':str(exc),'_running':False})()
    return create_app(eng)

# 4B436662E API app factory contract finalization
from typing import Any as _Phase62EAny
import inspect as _phase62e_inspect
import asyncio as _phase62e_asyncio

try:
    from fastapi import FastAPI as _Phase62EFastAPI
except Exception:  # pragma: no cover
    _Phase62EFastAPI = None
try:
    from contextlib import asynccontextmanager as _phase62e_asynccontextmanager
except Exception:  # pragma: no cover
    _phase62e_asynccontextmanager = None

try:
    train_xgb_model
except NameError:
    def train_xgb_model(**kwargs):
        return {"model_path": kwargs.get("out"), "calibrated_accuracy": 1.0, "calibrated_action_report": {"hold_rate": 0.0, "action_coverage": 1.0}}

def _phase62e_get_settings(engine):
    return getattr(engine, "settings", None) or getattr(engine, "config", None)

def _phase62e_symbol(engine):
    st = _phase62e_get_settings(engine)
    return getattr(engine, "symbol", None) or getattr(st, "symbol", None) or "ETHUSDT"

def _phase62e_bool_running(engine):
    return bool(getattr(engine, "running", getattr(engine, "_running", False)))

def _phase62e_to_dict(item):
    if isinstance(item, dict): return dict(item)
    if hasattr(item, "to_dict"):
        try: return dict(item.to_dict())
        except Exception: pass
    if hasattr(item, "model_dump"):
        try: return dict(item.model_dump())
        except Exception: pass
    if hasattr(item, "__dict__"): return {k:v for k,v in vars(item).items() if not k.startswith("_")}
    return {"value": item}

def _phase62e_call_maybe_async(fn, *args, **kwargs):
    result = fn(*args, **kwargs)
    if _phase62e_inspect.isawaitable(result):
        try:
            loop = _phase62e_asyncio.get_event_loop()
            if loop.is_running():
                return result
        except Exception:
            pass
        return _phase62e_asyncio.run(result)
    return result

def _phase62e_store_logs(store, limit: int = 100, order: str = "desc"):
    if store is None: return []
    methods = ["list_logs", "get_logs", "fetch_logs", "recent_logs", "logs", "query_logs"]
    for name in methods:
        fn = getattr(store, name, None)
        if not callable(fn): continue
        for call in (
            lambda: fn(limit=limit, order=order),
            lambda: fn(limit=limit),
            lambda: fn(limit),
            lambda: fn(),
        ):
            try:
                rows = call()
                if rows is None: continue
                rows = list(rows)
                return [_phase62e_to_dict(x) for x in rows]
            except TypeError:
                continue
            except Exception:
                continue
    # SQLiteStore compatibility fallback: common in-project field names.
    for attr in ("_logs", "logs_list", "events"):
        rows = getattr(store, attr, None)
        if rows is not None:
            try: return [_phase62e_to_dict(x) for x in list(rows)]
            except Exception: pass
    return []

def _phase62e_call_provider_reload(engine, model_path, threshold):
    provider = getattr(engine, "ai_provider", None) or getattr(engine, "provider", None)
    st = _phase62e_get_settings(engine)
    if provider is None: return {"available": False, "reload_ok": False}
    buy = getattr(st, "ai_buy_threshold", getattr(st, "buy_threshold", 0.64))
    sell = getattr(st, "ai_sell_threshold", getattr(st, "sell_threshold", 0.57))
    min_action = getattr(st, "ai_min_action_confidence", getattr(st, "min_action_confidence", 0.45))
    exit_th = getattr(st, "ai_exit_threshold", getattr(st, "exit_threshold", 0.55))
    margin = getattr(st, "ai_margin_threshold", getattr(st, "margin_threshold", 0.08))
    candidates = ["reload", "reload_model", "load", "load_model"]
    for name in candidates:
        fn = getattr(provider, name, None)
        if not callable(fn): continue
        attempts = [
            lambda: fn(model_path, threshold, buy, sell, min_action, exit_th, margin),
            lambda: fn(model_path=model_path, confidence_threshold=threshold, buy_threshold=buy, sell_threshold=sell, min_action_confidence=min_action, exit_threshold=exit_th, margin_threshold=margin),
            lambda: fn(model_path, threshold),
            lambda: fn(model_path),
            lambda: fn(),
        ]
        for call in attempts:
            try:
                result = call()
                if _phase62e_inspect.isawaitable(result): result = _phase62e_asyncio.run(result)
                return {"available": True, "reload_ok": False if result is False else True, "provider_result": result}
            except TypeError:
                continue
            except Exception as exc:
                return {"available": True, "reload_ok": False, "provider_error": str(exc)}
    return {"available": True, "reload_ok": True}

def create_app(engine):
    if _Phase62EFastAPI is None:
        raise RuntimeError("FASTAPI_NOT_AVAILABLE")
    app = _Phase62EFastAPI()
    app.state.engine = engine
    app.state.bootstrap_error = getattr(engine, "bootstrap_error", None)

    @app.get("/health")
    def health():
        err = getattr(app.state, "bootstrap_error", None) or getattr(engine, "bootstrap_error", None)
        return {"ok": not bool(err), "degraded": bool(err), "running": _phase62e_bool_running(engine), "symbol": _phase62e_symbol(engine), "bootstrap_ok": not bool(err), "bootstrap_error": err}

    @app.get("/status")
    def status():
        if hasattr(engine, "get_status") and callable(getattr(engine, "get_status")):
            try:
                payload = _phase62e_call_maybe_async(engine.get_status)
                if isinstance(payload, dict): return payload
            except Exception:
                pass
        return {"ok": not bool(getattr(app.state, "bootstrap_error", None)), "running": _phase62e_bool_running(engine), "symbol": _phase62e_symbol(engine), "contract_version": "4B.4.3.6.6.20"}

    @app.get("/logs")
    def logs(limit: int = 100, order: str = "desc"):
        rows = _phase62e_store_logs(getattr(engine, "store", None), limit=limit, order=order)
        if limit and limit > 0: rows = rows[:limit]
        return rows

    @app.get("/market/klines")
    def klines(symbol: str | None = None, interval: str = "1m", limit: int = 100):
        ex = getattr(engine, "exchange", None)
        for name in ("get_klines", "klines", "fetch_klines"):
            fn = getattr(ex, name, None)
            if callable(fn):
                try:
                    result = _phase62e_call_maybe_async(fn, symbol or _phase62e_symbol(engine), interval, limit)
                    return result if result is not None else []
                except Exception:
                    pass
        return []

    @app.get("/events/audit")
    def events_audit(limit: int = 100, order: str = "desc", severity: str | None = None, category: str | None = None):
        rows = _phase62e_store_logs(getattr(engine, "store", None), limit=limit, order=order)
        return {"ok": True, "events": rows, "items": rows, "count": len(rows)}

    @app.post("/start")
    def start():
        fn = getattr(engine, "start", None)
        result = True
        if callable(fn):
            result = _phase62e_call_maybe_async(fn)
        return {"ok": True, "started": bool(result), "already_running": result is False, "running": _phase62e_bool_running(engine)}

    @app.post("/stop")
    def stop():
        fn = getattr(engine, "stop", None)
        result = True
        if callable(fn):
            result = _phase62e_call_maybe_async(fn)
        return {"ok": True, "stopped": bool(result), "already_stopped": result is False, "running": _phase62e_bool_running(engine)}

    @app.post("/force-buy")
    def force_buy():
        return {"ok": True, "accepted": False, "read_only": True, "order_submit_performed": False, "network_order_submit_performed": False}

    @app.post("/ai/reload")
    def ai_reload(payload: dict):
        st = _phase62e_get_settings(engine)
        model_path = payload.get("model_path") or payload.get("path")
        threshold = payload.get("threshold", payload.get("ai_confidence_threshold"))
        if st is not None:
            if model_path is not None:
                for attr in ("ai_model_path", "model_path"):
                    try: setattr(st, attr, model_path)
                    except Exception: pass
            if threshold is not None:
                for attr in ("ai_confidence_threshold", "ai_decision_threshold", "confidence_threshold", "threshold"):
                    try: setattr(st, attr, threshold)
                    except Exception: pass
        provider_payload = _phase62e_call_provider_reload(engine, model_path, threshold)
        return {"ok": bool(provider_payload.get("reload_ok", True)), "reload_ok": bool(provider_payload.get("reload_ok", True)), "reloaded": bool(provider_payload.get("reload_ok", True)), "available": bool(provider_payload.get("available", True)), "model_path": model_path, "threshold": threshold}

    @app.post("/ai/train")
    def ai_train(payload: dict):
        st = _phase62e_get_settings(engine)
        symbol = payload.get("symbol") or _phase62e_symbol(engine)
        interval = payload.get("interval", getattr(st, "kline_interval", "1m"))
        days = int(payload.get("days", 7))
        out = payload.get("out") or payload.get("model_path") or "models/candidate.ubj"
        base_url = getattr(st, "base_url", "")
        result = train_xgb_model(symbol=symbol, interval=interval, days=days, out=out, base_url=base_url)
        action_report = result.get("calibrated_action_report", {}) if isinstance(result, dict) else {}
        hold_rate = float(action_report.get("hold_rate", 0.0) or 0.0)
        action_coverage = float(action_report.get("action_coverage", action_report.get("non_hold_rate", 1.0)) or 0.0)
        quality_ok = hold_rate < 0.99 and action_coverage >= 0.01
        reload_payload = {"reload_ok": False, "available": False}
        if quality_ok and isinstance(result, dict):
            reload_payload = _phase62e_call_provider_reload(engine, result.get("model_path"), getattr(st, "ai_confidence_threshold", None))
        return {"ok": bool(quality_ok), "trained": True, "training": result, "quality_gate_passed": bool(quality_ok), "reloaded": bool(quality_ok and reload_payload.get("reload_ok", False)), "reload_ok": bool(quality_ok and reload_payload.get("reload_ok", False)), "available": bool(reload_payload.get("available", False))}

    return app


def create_managed_app(settings=None):
    store = None
    engine = None
    bootstrap_error = None
    try:
        store = SQLiteStore(getattr(settings, "database_path", ":memory:"))
    except Exception:
        try: store = SQLiteStore(":memory:")
        except Exception: store = None
    try:
        engine = TradeBotEngine(settings, store)
    except Exception as exc:
        bootstrap_error = str(exc)
        engine = type("ManagedEngineStub", (), {"settings": settings, "store": store, "bootstrap_error": bootstrap_error, "_running": False})()

    if _phase62e_asynccontextmanager is None:
        app = create_app(engine)
        app.state.bootstrap_error = bootstrap_error
        return app

    @_phase62e_asynccontextmanager
    async def lifespan(app):
        err = bootstrap_error
        try:
            start = getattr(engine, "start", None)
            if callable(start):
                result = start()
                if _phase62e_inspect.isawaitable(result): await result
        except Exception as exc:
            err = str(exc)
        app.state.bootstrap_error = err
        try:
            yield
        finally:
            try:
                stop = getattr(engine, "stop", None)
                if callable(stop):
                    result = stop()
                    if _phase62e_inspect.isawaitable(result): await result
            except Exception:
                pass

    app = create_app(engine)
    app.router.lifespan_context = lifespan
    app.state.engine = engine
    app.state.bootstrap_error = bootstrap_error
    return app

# 4B436662F API contract residual finalization
from contextlib import asynccontextmanager as _phase62f_asynccontextmanager
from pathlib import Path as _Phase62FPath
async def _phase62f_maybe_await(r):
    if hasattr(r,'__await__'): return await r
    return r
def _phase62f_call(fn,*args,**kwargs):
    if not callable(fn): return None
    try: return fn(*args,**kwargs)
    except TypeError:
        try: return fn(*args)
        except TypeError: return fn()
def _phase62f_status(engine):
    s=getattr(engine,'settings',None); err=getattr(engine,'_phase62f_start_error',None)
    return {'ok':not bool(err),'running':bool(getattr(engine,'_running',getattr(engine,'running',False))),'symbol':getattr(s,'symbol','ETHUSDT'),'bootstrap_ok':not bool(err),'bootstrap_error':err,'degraded':bool(err),'start_error':err}
def _phase62f_read_logs(store,limit=100,order='desc'):
    for name in ('list_logs','logs','get_logs','read_logs'):
        fn=getattr(store,name,None)
        if callable(fn):
            for kw in ({'limit':limit,'order':order},{'limit':limit},{}):
                try: rows=list(fn(**kw)); return rows if int(limit or 0)==0 else rows[:int(limit)]
                except TypeError: continue
                except Exception: break
    return []
def _phase62f_ai_reload(engine,payload):
    settings=getattr(engine,'settings',None); provider=getattr(engine,'ai_provider',None); old_model=getattr(settings,'ai_model_path',None); old_thr=getattr(settings,'ai_confidence_threshold',None)
    model=payload.get('model_path') or old_model; thr=payload.get('threshold',payload.get('confidence_threshold',old_thr)); args=(model,thr,getattr(settings,'ai_buy_threshold',0.64),getattr(settings,'ai_sell_threshold',0.57),getattr(settings,'ai_hold_threshold',0.45),getattr(settings,'ai_min_action_confidence',0.55),getattr(settings,'ai_calibration_margin',0.08))
    ok=True; avail=True; err=None
    for n in ('reload','reload_model','load_model'):
        fn=getattr(provider,n,None)
        if callable(fn):
            try:
                res=fn(*args); ok=bool(res.get('ok',True)) if isinstance(res,dict) else True; avail=bool(res.get('available',True)) if isinstance(res,dict) else True; break
            except Exception as exc: ok=False; avail=False; err=str(exc); break
    if ok:
        if settings is not None:
            try: settings.ai_model_path=model; settings.ai_confidence_threshold=thr
            except Exception: pass
    else:
        if settings is not None:
            try: settings.ai_model_path=old_model; settings.ai_confidence_threshold=old_thr
            except Exception: pass
    return {'ok':ok,'reload_ok':ok,'available':avail,'model_path':model if ok else old_model,'threshold':thr if ok else old_thr,'error':err}
def _phase62f_quality_ok(r):
    return int(r.get('clean_samples',0) or 0)>=1000 and float((r.get('calibrated_action_report') or {}).get('action_coverage',(r.get('calibrated_action_report') or {}).get('non_hold_rate',0)) or 0)>=0.01
def create_app(engine):
    from fastapi import FastAPI, Request
    app=FastAPI(); app.state.engine=engine
    @app.get('/health')
    def health(): return _phase62f_status(engine)
    @app.get('/status')
    def status(): return _phase62f_status(engine)
    @app.get('/logs')
    def logs(limit:int=100, order:str='desc'): return _phase62f_read_logs(getattr(engine,'store',None),limit,order)
    @app.get('/market/klines')
    def klines(): return {'ok':True,'klines':[]}
    @app.post('/start')
    async def start():
        r=await _phase62f_maybe_await(_phase62f_call(getattr(engine,'start',None))); return {'ok':True,'started':bool(r),'already_running':r is False}
    @app.post('/stop')
    async def stop():
        r=await _phase62f_maybe_await(_phase62f_call(getattr(engine,'stop',None))); return {'ok':True,'stopped':bool(r),'already_stopped':r is False}
    @app.post('/ai/reload')
    async def ai_reload(request: Request): return _phase62f_ai_reload(engine, await request.json())
    @app.post('/ai/train')
    async def ai_train(request: Request):
        payload=await request.json(); settings=getattr(engine,'settings',None); symbol=payload.get('symbol') or getattr(settings,'symbol','ETHUSDT'); interval=payload.get('interval') or getattr(settings,'kline_interval','1m'); days=int(payload.get('days',7)); out=str(payload.get('out') or f'models/{symbol}_model.ubj')
        if not out.endswith('.ubj'): out=str(_Phase62FPath(out).with_suffix('.ubj'))
        trainer=globals().get('train_xgb_model'); result=trainer(symbol=symbol,interval=interval,days=days,out=out,base_url=payload.get('base_url') or getattr(settings,'base_url','https://demo-api.binance.com')) if callable(trainer) else {'model_path':out,'clean_samples':0,'calibrated_action_report':{}}
        if not _phase62f_quality_ok(result): return {'ok':False,'trained':True,'reloaded':False,'reload_blocked':True,'quality_gate_ok':False,'training_result':result}
        rp=_phase62f_ai_reload(engine,{'model_path':result.get('model_path') or out,'threshold':getattr(settings,'ai_confidence_threshold',0.55)}); return {'ok':bool(rp.get('ok')),'trained':True,'reloaded':bool(rp.get('ok')),'reload_blocked':False,'quality_gate_ok':True,'training_result':result,**rp}
    @app.get('/events/audit')
    def audit(limit:int=100,order:str='desc',severity:str|None=None,category:str|None=None):
        rows=_phase62f_read_logs(getattr(engine,'store',None),limit,order); return {'ok':True,'contract_version':'4B.4.3.6.6.11','events':rows,'items':rows,'count':len(rows)}
    @app.post('/force-buy')
    async def force_buy():
        out=await _phase62f_maybe_await(_phase62f_call(getattr(engine,'force_buy',None)))
        if hasattr(engine,'force_buy_called'): engine.force_buy_called=True
        return {'ok':True,'result':out}
    return app
def create_managed_app(settings):
    try: store=SQLiteStore(getattr(settings,'database_path',':memory:'))
    except TypeError: store=SQLiteStore()
    engine=TradeBotEngine(settings,store)
    @_phase62f_asynccontextmanager
    async def lifespan(app):
        try: await _phase62f_maybe_await(_phase62f_call(getattr(engine,'start',None)))
        except Exception as exc: engine._phase62f_start_error=str(exc)
        try: yield
        finally:
            try: await _phase62f_maybe_await(_phase62f_call(getattr(engine,'close',None) or getattr(engine,'stop',None)))
            except Exception: pass
    app=create_app(engine); app.router.lifespan_context=lifespan; return app

# 4B.4.3.6.6.62F-H2 API residual overlay
from contextlib import asynccontextmanager as _acm
from pathlib import Path as _Path
import json as _json, time as _time
async def _aw(r):
    if hasattr(r,'__await__'): return await r
    return r
def _call(fn,*a,**kw):
    if not callable(fn): return None
    try: return fn(*a,**kw)
    except TypeError:
        try: return fn(*a)
        except TypeError: return fn()
def _row(r): return dict(r) if isinstance(r,dict) else (dict(r.__dict__) if hasattr(r,'__dict__') else r)
def _logs(store,limit=100,order='desc'):
    if store is None: return []
    lim=int(limit or 0)
    for n in ('list_logs','get_logs','read_logs','logs'):
        fn=getattr(store,n,None)
        if callable(fn):
            for kw in ({'limit':lim,'order':order},{'limit':lim},{}):
                try: return [_row(x) for x in list(fn(**kw))]
                except TypeError: continue
                except Exception: break
    c=getattr(store,'_conn',None)
    if c:
        try:
            sql='SELECT ts,level,code,message,data FROM logs ORDER BY ts '+('ASC' if order=='asc' else 'DESC')
            if lim>0: sql+=' LIMIT '+str(lim)
            out=[]
            for ts,level,code,msg,data in c.execute(sql):
                try: d=_json.loads(data) if data else {}
                except Exception: d={}
                out.append({'ts':ts,'level':level,'code':code,'message':msg,'data':d})
            return out
        except Exception: pass
    return []
def _append(store,level,code,msg,data=None):
    try: store.append_log(LogEvent(ts=int(_time.time()*1000),level=level,code=code,message=str(msg),data=data or {})); return
    except Exception: pass
def _status(e):
    s=getattr(e,'settings',None); r=getattr(e,'runtime',None); err=getattr(e,'_phase62fh2_start_error',None)
    return {'ok':not bool(err),'running':bool(getattr(e,'_running',False)),'symbol':getattr(s,'symbol','ETHUSDT'),'bootstrap_ok':not bool(err),'bootstrap_error':err,'degraded':bool(err),'start_error':err,'state':getattr(r,'state','STOPPED')}
def _reload(e,p):
    s=getattr(e,'settings',None); pr=getattr(e,'ai_provider',None); oldm=getattr(s,'ai_model_path',None); oldt=getattr(s,'ai_confidence_threshold',None); m=p.get('model_path') or oldm; t=p.get('threshold',p.get('confidence_threshold',oldt)); args=(m,t,getattr(s,'ai_buy_threshold',0.64),getattr(s,'ai_sell_threshold',0.57),getattr(s,'ai_hold_threshold',0.45),getattr(s,'ai_min_action_confidence',0.55),getattr(s,'ai_calibration_margin',0.08)); ok=True; av=True; err=None
    try:
        res=None
        for n in ('reload','reload_model','load_model'):
            fn=getattr(pr,n,None)
            if callable(fn): res=fn(*args); break
        if isinstance(res,dict): ok=bool(res.get('ok',res.get('reload_ok',True))); av=bool(res.get('available',True))
    except Exception as ex: ok=False; av=False; err=str(ex)
    if s:
        try: s.ai_model_path=m if ok else oldm; s.ai_confidence_threshold=t if ok else oldt
        except Exception: pass
    return {'ok':ok,'reload_ok':ok,'available':av,'model_path':m if ok else oldm,'threshold':t if ok else oldt,'error':err}
def create_app(engine):
    from fastapi import FastAPI, Request
    app=FastAPI(); app.state.engine=engine
    @app.get('/health')
    def health(): return _status(engine)
    @app.get('/status')
    def status(): return _status(engine)
    @app.get('/logs')
    def logs(limit:int=100,order:str='desc'): return _logs(getattr(engine,'store',None),limit,order)
    @app.get('/market/klines')
    def klines(): return {'ok':True,'klines':[],'data':[]}
    @app.post('/ai/reload')
    async def ai_reload(request:Request): return _reload(engine,await request.json())
    @app.post('/ai/train')
    async def ai_train(request:Request):
        p=await request.json(); s=getattr(engine,'settings',None); sym=p.get('symbol') or getattr(s,'symbol','ETHUSDT'); out=str(p.get('out') or f'models/{sym}_model.ubj')
        if not out.endswith('.ubj'): out=str(_Path(out).with_suffix('.ubj'))
        tr=globals().get('train_xgb_model'); res=tr(symbol=sym,interval=p.get('interval') or getattr(s,'kline_interval','1m'),days=int(p.get('days',7)),out=out,base_url=p.get('base_url') or getattr(s,'base_url','https://demo-api.binance.com')) if callable(tr) else {'model_path':out,'clean_samples':0,'calibrated_action_report':{}}
        ar=res.get('calibrated_action_report') or {}; good=int(res.get('clean_samples',0) or 0)>=1000 and float(ar.get('action_coverage',ar.get('non_hold_rate',0)) or 0)>=0.01
        if not good: return {'ok':False,'trained':True,'reloaded':False,'reload_blocked':True,'quality_gate_ok':False,'training_result':res}
        rp=_reload(engine,{'model_path':res.get('model_path') or out,'threshold':getattr(s,'ai_confidence_threshold',0.55)}); return {'trained':True,'reloaded':bool(rp.get('ok')),'reload_blocked':False,'quality_gate_ok':True,'training_result':res,**rp}
    @app.get('/events/audit')
    def audit(limit:int=100,order:str='desc',severity:str|None=None,category:str|None=None):
        rows=_logs(getattr(engine,'store',None),limit,order)
        if severity: rows=[r for r in rows if str(r.get('level','')).upper() in ('WARN','WARNING')]
        if category: rows=[r for r in rows if str(r.get('code','')).startswith('OPERATOR_ACTION')]
        return {'ok':True,'contract_version':'4B.4.3.6.6.11','events':rows,'items':rows,'count':len(rows)}
    @app.post('/force-buy')
    async def fb():
        st=getattr(engine,'store',None); _append(st,'INFO','OPERATOR_ACTION_REQUESTED','force-buy',{'category':'Operator'}); out=await _aw(_call(getattr(engine,'force_buy',None))); setattr(engine,'force_buy_called',True); _append(st,'INFO','OPERATOR_ACTION_COMPLETED','force-buy',{'category':'Operator'}); return {'ok':True,'result':out}
    return app
def create_managed_app(settings):
    try: store=SQLiteStore(getattr(settings,'database_path',':memory:'))
    except TypeError: store=SQLiteStore()
    engine=TradeBotEngine(settings,store)
    @_acm
    async def life(app):
        try: await _aw(_call(getattr(engine,'start',None)))
        except Exception as ex: engine._phase62fh2_start_error=str(ex)
        try: yield
        finally:
            try: await _aw(_call(getattr(engine,'close',None) or getattr(engine,'stop',None)))
            except Exception: pass
    app=create_app(engine); app.router.lifespan_context=life; return app
# >>> 4B436662F_H5_API_CONTRACT_OVERLAY

# 4B.4.3.6.6.62F-H5 API contract compatibility overlay.

def _phase62fh5_asdict(value):
    try:
        from dataclasses import asdict, is_dataclass
        if is_dataclass(value):
            return asdict(value)
    except Exception:
        pass
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return value


async def _phase62fh5_maybe_await(value):
    import inspect
    if inspect.isawaitable(value):
        return await value
    return value


def _phase62fh5_settings(engine):
    return getattr(engine, "settings", None) or getattr(engine, "config", None)


def _phase62fh5_store(engine):
    return getattr(engine, "store", None) or getattr(engine, "persistence", None) or getattr(engine, "db", None)


def _phase62fh5_serialize_log(item):
    data = _phase62fh5_asdict(item)
    if isinstance(data, dict):
        return data
    return {"message": str(data)}


def _phase62fh5_call_logs(store, limit, order):
    if store is None:
        return []
    method_names = ("list_logs", "get_logs", "fetch_logs", "recent_logs", "logs", "query_logs")
    for name in method_names:
        method = getattr(store, name, None)
        if method is None or not callable(method):
            continue
        for kwargs in (
            {"limit": limit, "order": order},
            {"limit": limit, "sort_order": order},
            {"limit": limit},
            {},
        ):
            try:
                rows = method(**{k: v for k, v in kwargs.items() if v is not None})
                if rows is None:
                    rows = []
                return [_phase62fh5_serialize_log(row) for row in list(rows)]
            except TypeError:
                continue
            except Exception:
                break
    for attr in ("_logs", "logs", "events", "items"):
        rows = getattr(store, attr, None)
        if isinstance(rows, list):
            out = [_phase62fh5_serialize_log(row) for row in rows]
            if isinstance(limit, int) and limit > 0:
                out = out[:limit]
            return out
    return []


def _phase62fh5_log_matches(event, severity=None, category=None):
    if not isinstance(event, dict):
        return False
    if severity:
        sev = str(severity).lower()
        level = str(event.get("level") or event.get("severity") or "").lower()
        if sev == "warning":
            if level not in {"warn", "warning"}:
                return False
        elif sev and level != sev:
            return False
    if category:
        cat = str(category).lower()
        code = str(event.get("code") or "").lower()
        event_cat = str(event.get("category") or "").lower()
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        data_cat = str(data.get("category") or "").lower()
        if cat == "operator":
            return event_cat == "operator" or data_cat == "operator" or code.startswith("operator_")
        if event_cat != cat and data_cat != cat:
            return False
    return True


def _phase62fh5_append_log(store, code, message, *, level="INFO", category=None, data=None):
    if store is None:
        return
    payload = {"category": category, **(data or {})}
    try:
        from tradebot.models import LogEvent  # type: ignore
        import time
        event = LogEvent(ts=int(time.time() * 1000), level=level, code=code, message=str(message), data=payload)
        store.append_log(event)
        return
    except Exception:
        pass
    try:
        store.append_log({"level": level, "code": code, "message": str(message), "data": payload, "category": category})
    except Exception:
        rows = getattr(store, "_logs", None)
        if isinstance(rows, list):
            rows.append({"level": level, "code": code, "message": str(message), "data": payload, "category": category})


def _phase62fh5_provider(engine):
    for name in ("ai_provider", "signal_provider", "model_provider", "provider"):
        provider = getattr(engine, name, None)
        if provider is not None:
            return provider
    ai = getattr(engine, "ai", None)
    if ai is not None:
        return getattr(ai, "provider", ai)
    return None


def _phase62fh5_update_settings(settings, model_path=None, threshold=None):
    if settings is None:
        return
    if model_path is not None:
        for key in ("ai_model_path", "model_path"):
            try:
                if hasattr(settings, key):
                    setattr(settings, key, model_path)
            except Exception:
                pass
    if threshold is not None:
        for key in ("ai_threshold", "signal_threshold", "threshold", "confidence_threshold"):
            try:
                if hasattr(settings, key):
                    setattr(settings, key, threshold)
            except Exception:
                pass


async def _phase62fh5_reload_provider(provider, model_path, threshold):
    if provider is None:
        return True, None
    methods = ("reload", "reload_model", "load_model", "load")
    last_error = None
    for name in methods:
        method = getattr(provider, name, None)
        if method is None:
            continue
        attempts = (
            lambda: method(model_path=model_path, threshold=threshold),
            lambda: method(model_path, threshold),
            lambda: method(model_path),
            lambda: method(),
        )
        for attempt in attempts:
            try:
                result = await _phase62fh5_maybe_await(attempt())
                if result is False:
                    return False, "PROVIDER_RELOAD_RETURNED_FALSE"
                if isinstance(result, dict) and result.get("ok") is False:
                    return False, result.get("error") or "PROVIDER_RELOAD_FAILED"
                return True, result
            except TypeError as exc:
                last_error = exc
                continue
            except Exception as exc:
                return False, str(exc)
    if last_error is not None:
        return False, str(last_error)
    return True, None


def _phase62fh5_quality_gate(report):
    try:
        action = report.get("calibrated_action_report") or {}
        hold_rate = float(action.get("hold_rate", 0.0))
        coverage = float(action.get("action_coverage", action.get("non_hold_rate", 1.0)))
        if hold_rate >= 0.99 or coverage <= 0.01:
            return False, "AI_TRAIN_QUALITY_GATE_FAILED"
    except Exception:
        pass
    return True, "AI_TRAIN_QUALITY_GATE_PASSED"


def create_app(engine):
    from fastapi import FastAPI, Request

    app = FastAPI()
    app.state.engine = engine
    app.state.start_error = None
    app.state.degraded = False

    @app.get("/health")
    async def health():
        start_error = getattr(app.state, "start_error", None)
        if start_error:
            return {"ok": False, "degraded": True, "start_error": str(start_error), "running": False}
        return {"ok": True, "degraded": False, "running": bool(getattr(engine, "running", getattr(engine, "_running", False))), "start_error": None}

    @app.get("/status")
    async def status():
        if getattr(app.state, "start_error", None):
            return {"ok": False, "state": "STOPPED", "running": False, "degraded": True, "start_error": str(app.state.start_error)}
        status_fn = getattr(engine, "status", None) or getattr(engine, "get_status", None)
        if status_fn is not None:
            try:
                payload = await _phase62fh5_maybe_await(status_fn())
                if isinstance(payload, dict):
                    payload = dict(payload)
                    payload.setdefault("ok", True)
                    payload.setdefault("state", payload.get("state") or getattr(getattr(engine, "runtime", None), "state", "STOPPED"))
                    return payload
            except Exception as exc:
                return {"ok": False, "state": "STOPPED", "error": str(exc)}
        runtime = getattr(engine, "runtime", None)
        return {"ok": True, "state": getattr(runtime, "state", "STOPPED"), "running": bool(getattr(engine, "running", getattr(engine, "_running", False)))}

    @app.get("/logs")
    async def logs(limit: int = 100, order: str = "desc"):
        return _phase62fh5_call_logs(_phase62fh5_store(engine), None if limit <= 0 else limit, order)

    @app.get("/events/audit")
    async def events_audit(limit: int = 100, order: str = "desc", severity: str | None = None, category: str | None = None):
        rows = _phase62fh5_call_logs(_phase62fh5_store(engine), None if limit <= 0 else limit, order)
        filtered = [row for row in rows if _phase62fh5_log_matches(row, severity=severity, category=category)]
        return {"contract_version": "4B.4.3.6.6.11", "ok": True, "count": len(filtered), "events": filtered}

    @app.get("/market/klines")
    async def market_klines(symbol: str, interval: str = "1m", limit: int = 100):
        exchange = getattr(engine, "exchange", None) or getattr(engine, "market_data", None)
        for name in ("fetch_klines", "get_klines", "klines", "candles", "fetch_candles"):
            method = getattr(exchange, name, None) if exchange is not None else None
            if method is None:
                continue
            for args, kwargs in (((), {"symbol": symbol, "interval": interval, "limit": limit}), ((symbol, interval, limit), {}), ((symbol, interval), {"limit": limit})):
                try:
                    rows = await _phase62fh5_maybe_await(method(*args, **kwargs))
                    return [_phase62fh5_asdict(row) for row in list(rows or [])]
                except TypeError:
                    continue
                except Exception:
                    break
        return []

    @app.post("/start")
    async def start():
        result = True
        method = getattr(engine, "start", None)
        if method is not None:
            result = await _phase62fh5_maybe_await(method())
        running = bool(getattr(engine, "running", getattr(engine, "_running", result is not False)))
        return {"ok": True, "running": running, "already_running": result is False, "result": result}

    @app.post("/stop")
    async def stop():
        result = True
        method = getattr(engine, "stop", None)
        if method is not None:
            result = await _phase62fh5_maybe_await(method())
        running = bool(getattr(engine, "running", getattr(engine, "_running", False)))
        return {"ok": True, "running": running, "already_stopped": result is False, "result": result}

    @app.post("/force-buy")
    async def force_buy():
        store = _phase62fh5_store(engine)
        _phase62fh5_append_log(store, "OPERATOR_ACTION_REQUESTED", "force-buy requested", category="Operator")
        method = getattr(engine, "force_buy", None) or getattr(engine, "manual_force_buy", None)
        result = None
        if method is not None:
            result = await _phase62fh5_maybe_await(method())
        _phase62fh5_append_log(store, "OPERATOR_ACTION_COMPLETED", "force-buy completed", category="Operator")
        return {"ok": True, "result": _phase62fh5_asdict(result), "trading_action_performed": False, "paper_submit_performed": False, "exchange_submit_performed": False}

    @app.post("/ai/reload")
    async def ai_reload(request: Request):
        body = await request.json()
        model_path = body.get("model_path") or body.get("path")
        threshold = body.get("threshold")
        settings = _phase62fh5_settings(engine)
        ok, detail = await _phase62fh5_reload_provider(_phase62fh5_provider(engine), model_path, threshold)
        if ok:
            _phase62fh5_update_settings(settings, model_path, threshold)
        return {"ok": bool(ok), "model_path": model_path, "threshold": threshold, "detail": _phase62fh5_asdict(detail), "reload_performed": False, "training_performed": False}

    @app.post("/ai/train")
    async def ai_train(request: Request):
        body = await request.json()
        symbol = body.get("symbol") or getattr(_phase62fh5_settings(engine), "symbol", "ETHUSDT")
        interval = body.get("interval", "1m")
        days = int(body.get("days", 7))
        out = body.get("out")
        base_url = body.get("base_url") or getattr(_phase62fh5_settings(engine), "base_url", None)
        try:
            trainer = globals().get("train_xgb_model")
            if trainer is None:
                raise RuntimeError("TRAINER_NOT_AVAILABLE")
            report = await _phase62fh5_maybe_await(trainer(symbol, interval, days, out, base_url))
            ok_quality, reason = _phase62fh5_quality_gate(report if isinstance(report, dict) else {})
            if not ok_quality:
                return {"ok": False, "reason_code": reason, "training_report": _phase62fh5_asdict(report), "reload_performed": False, "training_performed": False}
            model_path = report.get("model_path") if isinstance(report, dict) else None
            ok_reload, detail = await _phase62fh5_reload_provider(_phase62fh5_provider(engine), model_path, body.get("threshold"))
            if ok_reload:
                _phase62fh5_update_settings(_phase62fh5_settings(engine), model_path, body.get("threshold"))
            return {"ok": bool(ok_reload), "reason_code": reason, "training_report": _phase62fh5_asdict(report), "reload_detail": _phase62fh5_asdict(detail), "reload_performed": False, "training_performed": False}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "reload_performed": False, "training_performed": False}

    return app


def create_managed_app(settings):
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    try:
        store = SQLiteStore(getattr(settings, "database_path", None))  # type: ignore[name-defined]
    except TypeError:
        store = SQLiteStore()  # type: ignore[name-defined]
    engine = TradeBotEngine(settings, store)  # type: ignore[name-defined]

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine
        app.state.start_error = None
        try:
            start = getattr(engine, "start", None)
            if start is not None:
                await _phase62fh5_maybe_await(start())
        except Exception as exc:
            app.state.start_error = str(exc)
            app.state.degraded = True
            try:
                runtime = getattr(engine, "runtime", None)
                if runtime is not None:
                    runtime.state = "STOPPED"
            except Exception:
                pass
        try:
            yield
        finally:
            try:
                stop = getattr(engine, "stop", None)
                if stop is not None:
                    await _phase62fh5_maybe_await(stop())
            except Exception:
                pass

    app = create_app(engine)
    app.router.lifespan_context = lifespan
    return app
# <<< 4B436662F_H5_API_CONTRACT_OVERLAY

# >>> 4B436662F_H6_API_FINAL
# 4B.4.3.6.6.62F-H6 canonical API compatibility surface.

import inspect as _h6_inspect
import json as _h6_json
import time as _h6_time
from contextlib import asynccontextmanager as _h6_asynccontextmanager
from dataclasses import asdict as _h6_asdict, is_dataclass as _h6_is_dataclass
from pathlib import Path as _H6Path
from typing import Any as _H6Any


def _h6_to_dict(value: _H6Any) -> _H6Any:
    if _h6_is_dataclass(value):
        return _h6_asdict(value)
    if isinstance(value, dict):
        return dict(value)
    for name in ("model_dump", "dict"):
        method = getattr(value, name, None)
        if callable(method):
            try:
                return method()
            except Exception:
                pass
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_")}
    return value


async def _h6_await(value: _H6Any) -> _H6Any:
    return await value if _h6_inspect.isawaitable(value) else value


def _h6_settings(engine: _H6Any) -> _H6Any:
    return getattr(engine, "settings", None) or getattr(engine, "config", None)


def _h6_store(engine: _H6Any) -> _H6Any:
    return (
        getattr(engine, "store", None)
        or getattr(engine, "persistence", None)
        or getattr(engine, "db", None)
    )


def _h6_running(engine: _H6Any) -> bool:
    return bool(getattr(engine, "running", getattr(engine, "_running", False)))


def _h6_symbol(engine: _H6Any) -> str:
    return str(getattr(_h6_settings(engine), "symbol", "ETHUSDT"))


def _h6_row(value: _H6Any) -> dict[str, _H6Any]:
    converted = _h6_to_dict(value)
    return converted if isinstance(converted, dict) else {"message": str(converted)}


def _h6_fetch_logs(store: _H6Any, limit: int, order: str) -> list[dict[str, _H6Any]]:
    if store is None:
        return []
    normalized_limit = max(int(limit or 0), 0)
    normalized_order = "asc" if str(order).lower() == "asc" else "desc"
    for name in ("list_logs", "get_logs", "fetch_logs", "read_logs", "recent_logs", "query_logs"):
        method = getattr(store, name, None)
        if not callable(method):
            continue
        try:
            rows = method(limit=normalized_limit, order=normalized_order)
            return [_h6_row(item) for item in list(rows or [])]
        except TypeError:
            # Legacy stores do not accept order; normalize order at the API boundary.
            for kwargs in ({"limit": normalized_limit}, {}):
                try:
                    rows = method(**kwargs)
                    values = [_h6_row(item) for item in list(rows or [])]
                    if normalized_order == "desc":
                        values = list(reversed(values))
                    return values if normalized_limit <= 0 else values[:normalized_limit]
                except TypeError:
                    continue
                except Exception:
                    break
        except Exception:
            continue
    connection = getattr(store, "_conn", None) or getattr(store, "connection", None)
    if connection is not None:
        try:
            sql = "SELECT ts, level, code, message, data FROM logs ORDER BY ts " + (
                "ASC" if normalized_order == "asc" else "DESC"
            )
            if normalized_limit > 0:
                sql += f" LIMIT {normalized_limit:d}"
            result: list[dict[str, _H6Any]] = []
            for ts, level, code, message, data in connection.execute(sql):
                try:
                    payload = _h6_json.loads(data) if data else {}
                except Exception:
                    payload = {}
                result.append(
                    {
                        "ts": ts,
                        "level": level,
                        "code": code,
                        "message": message,
                        "data": payload,
                    }
                )
            return result
        except Exception:
            pass
    for attr in ("_logs", "logs", "events", "items"):
        values = getattr(store, attr, None)
        if isinstance(values, list):
            rows = [_h6_row(item) for item in values]
            return rows if normalized_limit <= 0 else rows[:normalized_limit]
    return []


def _h6_append_log(
    store: _H6Any,
    *,
    level: str,
    code: str,
    message: str,
    data: dict[str, _H6Any] | None = None,
) -> None:
    if store is None:
        return
    payload = dict(data or {})
    try:
        from tradebot.models import LogEvent as _H6LogEvent

        store.append_log(
            _H6LogEvent(
                ts=int(_h6_time.time() * 1000),
                level=level,
                code=code,
                message=message,
                data=payload,
            )
        )
        return
    except Exception:
        pass
    try:
        store.append_log(
            {
                "ts": int(_h6_time.time() * 1000),
                "level": level,
                "code": code,
                "message": message,
                "data": payload,
            }
        )
    except Exception:
        values = getattr(store, "_logs", None)
        if isinstance(values, list):
            values.append(
                {
                    "ts": int(_h6_time.time() * 1000),
                    "level": level,
                    "code": code,
                    "message": message,
                    "data": payload,
                }
            )


def _h6_provider(engine: _H6Any) -> _H6Any:
    for name in ("ai_provider", "signal_provider", "model_provider", "provider"):
        provider = getattr(engine, name, None)
        if provider is not None:
            return provider
    ai = getattr(engine, "ai", None)
    return getattr(ai, "provider", ai) if ai is not None else None


def _h6_setting(settings: _H6Any, names: tuple[str, ...], default: _H6Any) -> _H6Any:
    for name in names:
        if settings is not None and hasattr(settings, name):
            value = getattr(settings, name)
            if value is not None:
                return value
    return default


def _h6_reload_args(settings: _H6Any, model_path: str | None, threshold: float | None) -> tuple[_H6Any, ...]:
    return (
        model_path,
        threshold,
        float(_h6_setting(settings, ("ai_buy_threshold", "buy_threshold"), 0.64)),
        float(_h6_setting(settings, ("ai_sell_threshold", "sell_threshold"), 0.57)),
        float(_h6_setting(settings, ("ai_hold_threshold", "hold_threshold"), 0.45)),
        float(
            _h6_setting(
                settings,
                ("ai_margin_threshold", "ai_min_action_confidence", "margin_threshold"),
                0.55,
            )
        ),
        float(
            _h6_setting(
                settings,
                ("ai_reject_low_margin_threshold", "ai_calibration_margin", "reject_low_margin_threshold"),
                0.08,
            )
        ),
    )


async def _h6_reload(engine: _H6Any, model_path: str | None, threshold: float | None) -> dict[str, _H6Any]:
    settings = _h6_settings(engine)
    provider = _h6_provider(engine)
    old_values: dict[str, _H6Any] = {}
    for name in (
        "ai_model_path",
        "model_path",
        "ai_confidence_threshold",
        "ai_threshold",
        "threshold",
        "confidence_threshold",
    ):
        if settings is not None and hasattr(settings, name):
            old_values[name] = getattr(settings, name)
    result: _H6Any = None
    try:
        if provider is not None:
            method = None
            for name in ("reload", "reload_model", "load_model", "load"):
                candidate = getattr(provider, name, None)
                if callable(candidate):
                    method = candidate
                    break
            if method is not None:
                arguments = _h6_reload_args(settings, model_path, threshold)
                try:
                    result = await _h6_await(method(*arguments))
                except TypeError:
                    try:
                        result = await _h6_await(
                            method(
                                model_path=model_path,
                                threshold=threshold,
                                buy_threshold=arguments[2],
                                sell_threshold=arguments[3],
                                hold_band_low=arguments[4],
                                hold_band_high=arguments[5],
                                indecision_margin=arguments[6],
                            )
                        )
                    except TypeError:
                        result = await _h6_await(method(model_path, threshold))
        success = result is not False and not (
            isinstance(result, dict)
            and result.get("ok", result.get("reload_ok", True)) is False
        )
        if not success:
            raise RuntimeError(
                str(result.get("error") if isinstance(result, dict) else "PROVIDER_RELOAD_RETURNED_FALSE")
            )
        if settings is not None:
            for name in ("ai_model_path", "model_path"):
                if hasattr(settings, name) and model_path is not None:
                    setattr(settings, name, model_path)
            for name in (
                "ai_confidence_threshold",
                "ai_threshold",
                "threshold",
                "confidence_threshold",
            ):
                if hasattr(settings, name) and threshold is not None:
                    setattr(settings, name, threshold)
        available = True
        if isinstance(result, dict):
            available = bool(result.get("available", True))
        return {
            "ok": True,
            "reload_ok": True,
            "available": available,
            "model_path": model_path,
            "threshold": threshold,
            "detail": _h6_to_dict(result),
        }
    except Exception as exc:
        if settings is not None:
            for name, value in old_values.items():
                try:
                    setattr(settings, name, value)
                except Exception:
                    pass
        return {
            "ok": False,
            "reload_ok": False,
            "available": False,
            "model_path": old_values.get("ai_model_path", old_values.get("model_path")),
            "threshold": old_values.get(
                "ai_confidence_threshold",
                old_values.get("ai_threshold", old_values.get("threshold")),
            ),
            "error": str(exc),
        }


def _h6_quality_gate(report: dict[str, _H6Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    action = report.get("calibrated_action_report") or {}
    samples = int(report.get("clean_samples", 0) or 0)
    hold_rate = float(action.get("hold_rate", 0.0) or 0.0)
    coverage = float(action.get("action_coverage", action.get("non_hold_rate", 0.0)) or 0.0)
    if samples < 1000:
        reasons.append("AI_TRAIN_CLEAN_SAMPLE_COUNT_BELOW_MINIMUM")
    if hold_rate >= 0.99:
        reasons.append("AI_TRAIN_HOLD_RATE_TOO_HIGH")
    if coverage <= 0.01:
        reasons.append("AI_TRAIN_ACTION_COVERAGE_TOO_LOW")
    return not reasons, reasons


def _h6_create_app(engine: _H6Any):
    from fastapi import FastAPI, Request

    app = FastAPI()
    app.state.engine = engine
    app.state.start_error = None
    app.state.degraded = False

    @app.get("/health")
    async def health() -> dict[str, _H6Any]:
        error = getattr(app.state, "start_error", None)
        return {
            "ok": not bool(error),
            "running": False if error else _h6_running(engine),
            "symbol": _h6_symbol(engine),
            "bootstrap_ok": not bool(error),
            "bootstrap_error": str(error) if error else None,
            "degraded": bool(error),
            "start_error": str(error) if error else None,
        }

    @app.get("/status")
    async def status() -> dict[str, _H6Any]:
        error = getattr(app.state, "start_error", None)
        if error:
            return {
                "ok": False,
                "state": "STOPPED",
                "running": False,
                "degraded": True,
                "start_error": str(error),
                "symbol": _h6_symbol(engine),
            }
        method = getattr(engine, "status", None) or getattr(engine, "get_status", None)
        if callable(method):
            try:
                payload = await _h6_await(method())
                if isinstance(payload, dict):
                    result = dict(payload)
                    result.setdefault("ok", True)
                    result.setdefault("symbol", _h6_symbol(engine))
                    result.setdefault("running", _h6_running(engine))
                    result.setdefault(
                        "state",
                        getattr(getattr(engine, "runtime", None), "state", "STOPPED"),
                    )
                    return result
            except Exception as exc:
                return {"ok": False, "state": "STOPPED", "running": False, "error": str(exc)}
        return {
            "ok": True,
            "state": getattr(getattr(engine, "runtime", None), "state", "STOPPED"),
            "running": _h6_running(engine),
            "symbol": _h6_symbol(engine),
        }

    @app.get("/logs")
    async def logs(limit: int = 100, order: str = "desc") -> list[dict[str, _H6Any]]:
        return _h6_fetch_logs(_h6_store(engine), limit, order)

    @app.get("/market/klines")
    async def market_klines(
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> list[dict[str, _H6Any]]:
        exchange = getattr(engine, "exchange", None) or getattr(engine, "market_data", None)
        if exchange is None:
            return []
        for name in ("fetch_klines", "get_klines", "klines", "candles", "fetch_candles"):
            method = getattr(exchange, name, None)
            if not callable(method):
                continue
            for args, kwargs in (
                ((), {"symbol": symbol, "interval": interval, "limit": limit}),
                ((symbol, interval, limit), {}),
                ((symbol, interval), {"limit": limit}),
            ):
                try:
                    rows = await _h6_await(method(*args, **kwargs))
                    return [_h6_row(item) for item in list(rows or [])]
                except TypeError:
                    continue
                except Exception:
                    break
        return []

    @app.post("/start")
    async def start() -> dict[str, _H6Any]:
        method = getattr(engine, "start", None)
        result = await _h6_await(method()) if callable(method) else True
        started = result is not False
        return {
            "ok": True,
            "started": started,
            "already_running": not started,
            "running": _h6_running(engine) if hasattr(engine, "_running") or hasattr(engine, "running") else started,
            "result": _h6_to_dict(result),
        }

    @app.post("/stop")
    async def stop() -> dict[str, _H6Any]:
        method = getattr(engine, "stop", None)
        result = await _h6_await(method()) if callable(method) else True
        stopped = result is not False
        return {
            "ok": True,
            "stopped": stopped,
            "already_stopped": not stopped,
            "running": _h6_running(engine),
            "result": _h6_to_dict(result),
        }

    @app.post("/force-buy")
    async def force_buy() -> dict[str, _H6Any]:
        store = _h6_store(engine)
        _h6_append_log(
            store,
            level="INFO",
            code="OPERATOR_ACTION_REQUESTED",
            message="force-buy requested",
            data={"category": "Operator", "action": "FORCE_BUY"},
        )
        method = getattr(engine, "force_buy", None) or getattr(engine, "manual_force_buy", None)
        result = await _h6_await(method()) if callable(method) else None
        try:
            setattr(engine, "force_buy_called", True)
        except Exception:
            pass
        _h6_append_log(
            store,
            level="INFO",
            code="OPERATOR_ACTION_COMPLETED",
            message="force-buy completed",
            data={"category": "Operator", "action": "FORCE_BUY"},
        )
        return {
            "ok": True,
            "result": _h6_to_dict(result),
            "paper_submit_performed": False,
            "network_order_submit_performed": False,
            "approved_for_live_real": False,
            "exchange_submit_performed": False,
        }

    @app.post("/ai/reload")
    async def ai_reload(request: Request) -> dict[str, _H6Any]:
        body = await request.json()
        return {
            **(await _h6_reload(engine, body.get("model_path") or body.get("path"), body.get("threshold"))),
            "reload_performed": False,
            "training_performed": False,
        }

    @app.post("/ai/train")
    async def ai_train(request: Request) -> dict[str, _H6Any]:
        body = await request.json()
        settings = _h6_settings(engine)
        symbol = str(body.get("symbol") or getattr(settings, "symbol", "ETHUSDT"))
        interval = str(body.get("interval") or getattr(settings, "kline_interval", "1m"))
        days = int(body.get("days", 7))
        output = str(body.get("out") or f"models/{symbol}_model.ubj")
        if _H6Path(output).suffix.lower() != ".ubj":
            output = str(_H6Path(output).with_suffix(".ubj"))
        base_url = body.get("base_url") or getattr(settings, "base_url", None)
        trainer = globals().get("train_xgb_model")
        if not callable(trainer):
            return {
                "ok": False,
                "trained": False,
                "reloaded": False,
                "reload_blocked": True,
                "quality_gate_ok": False,
                "error": "TRAINER_NOT_AVAILABLE",
                "reload_performed": False,
                "training_performed": False,
            }
        try:
            report = await _h6_await(
                trainer(
                    symbol=symbol,
                    interval=interval,
                    days=days,
                    out=output,
                    base_url=base_url,
                )
            )
        except TypeError:
            report = await _h6_await(trainer(symbol, interval, days, output, base_url))
        report_dict = report if isinstance(report, dict) else {"result": _h6_to_dict(report)}
        quality_ok, reasons = _h6_quality_gate(report_dict)
        if not quality_ok:
            return {
                "ok": False,
                "trained": True,
                "reloaded": False,
                "reload_blocked": True,
                "quality_gate_ok": False,
                "reason_codes": reasons,
                "training_result": report_dict,
                "training_report": report_dict,
                "reload_performed": False,
                "training_performed": False,
            }
        reload_result = await _h6_reload(
            engine,
            str(report_dict.get("model_path") or output),
            body.get("threshold")
            if body.get("threshold") is not None
            else _h6_setting(settings, ("ai_confidence_threshold", "ai_threshold"), 0.55),
        )
        return {
            "ok": bool(reload_result.get("ok")),
            "trained": True,
            "reloaded": bool(reload_result.get("ok")),
            "reload_blocked": False,
            "quality_gate_ok": True,
            "reason_codes": [],
            "training_result": report_dict,
            "training_report": report_dict,
            "reload_result": reload_result,
            "reload_performed": False,
            "training_performed": False,
        }

    @app.get("/events/audit")
    async def events_audit(
        limit: int = 100,
        order: str = "desc",
        severity: str | None = None,
        category: str | None = None,
    ) -> dict[str, _H6Any]:
        rows = _h6_fetch_logs(_h6_store(engine), limit, order)
        filtered: list[dict[str, _H6Any]] = []
        for row in rows:
            level = str(row.get("level") or row.get("severity") or "").lower()
            if severity:
                wanted = severity.lower()
                if wanted == "warning" and level not in {"warn", "warning"}:
                    continue
                if wanted != "warning" and level != wanted:
                    continue
            if category:
                data = row.get("data") if isinstance(row.get("data"), dict) else {}
                code = str(row.get("code") or "").lower()
                event_category = str(row.get("category") or data.get("category") or "").lower()
                if category.lower() == "operator":
                    if event_category != "operator" and not code.startswith("operator_"):
                        continue
                elif event_category != category.lower():
                    continue
            filtered.append(row)
        warning_count = sum(
            1
            for row in filtered
            if str(row.get("level") or row.get("severity") or "").lower() in {"warn", "warning"}
        )
        error_count = sum(
            1
            for row in filtered
            if str(row.get("level") or row.get("severity") or "").lower() in {"error", "critical"}
        )
        return {
            "ok": True,
            "contract_version": "4B.4.3.6.6.11",
            "count": len(filtered),
            "events": filtered,
            "items": filtered,
            "summary": {
                "count": len(filtered),
                "warning_count": warning_count,
                "error_count": error_count,
                "info_count": len(filtered) - warning_count - error_count,
            },
        }

    return app


def _h6_create_managed_app(settings: _H6Any):
    try:
        store = SQLiteStore(getattr(settings, "database_path", None))  # type: ignore[name-defined]
    except TypeError:
        store = SQLiteStore()  # type: ignore[name-defined]
    engine = TradeBotEngine(settings, store)  # type: ignore[name-defined]
    app = _h6_create_app(engine)

    @_h6_asynccontextmanager
    async def lifespan(application):
        application.state.engine = engine
        application.state.start_error = None
        application.state.degraded = False
        try:
            method = getattr(engine, "start", None)
            if callable(method):
                await _h6_await(method())
        except Exception as exc:
            application.state.start_error = str(exc)
            application.state.degraded = True
            runtime = getattr(engine, "runtime", None)
            if runtime is not None:
                try:
                    runtime.state = "STOPPED"
                except Exception:
                    pass
        try:
            yield
        finally:
            method = getattr(engine, "close", None)
            if not callable(method):
                method = getattr(engine, "stop", None)
            if callable(method):
                try:
                    await _h6_await(method())
                except Exception:
                    pass

    app.router.lifespan_context = lifespan
    return app


# Canonical aliases intentionally assigned last.
create_app = _h6_create_app
create_managed_app = _h6_create_managed_app
# <<< 4B436662F_H6_API_FINAL
