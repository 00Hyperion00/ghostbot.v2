from __future__ import annotations

from typing import Any

DECISION_AUDIT_CONTRACT_VERSION = '4B.4.3.6.6.19'


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == '':
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == '':
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _decision_dict(decision: Any | None) -> dict[str, Any]:
    if decision is None:
        return {
            'signal': 'HOLD',
            'trend': 'UNKNOWN',
            'reason': '-',
            'provider': None,
            'confidence': None,
            'last_evaluated_close_time': None,
        }
    return {
        'signal': str(getattr(decision, 'signal', 'HOLD') or 'HOLD'),
        'trend': str(getattr(decision, 'trend', 'UNKNOWN') or 'UNKNOWN'),
        'reason': str(getattr(decision, 'reason', '-') or '-'),
        'provider': getattr(decision, 'provider', None),
        'confidence': _safe_float(getattr(decision, 'confidence', None)),
        'last_evaluated_close_time': _safe_int(getattr(decision, 'last_evaluated_close_time', None)),
    }


def _metric(metrics: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in metrics:
            return metrics.get(name)
    return None


def build_decision_audit_snapshot(
    *,
    now: int,
    symbol: str,
    interval: str,
    settings: Any,
    runtime: Any,
    technical_decision: Any | None,
    model_decision: Any | None,
    effective_decision: Any | None = None,
    signal_key: str | None = None,
    action: str = 'EVALUATED',
    should_submit_order: bool = False,
    skip_code: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, non-blocking strategy decision audit snapshot.

    The snapshot is observe-only: it explains what the strategy decided and what
    the auto-trade layer intended, but it never changes the decision itself.
    """
    technical = _decision_dict(technical_decision)
    model = _decision_dict(model_decision)
    effective = _decision_dict(effective_decision or model_decision)
    metrics = dict(getattr(model_decision, 'metrics', None) or {})

    raw_signal = model.get('signal') or 'HOLD'
    effective_signal = effective.get('signal') or raw_signal
    action_intent = 'NONE'
    if effective_signal == 'BUY':
        action_intent = 'ENTRY'
    elif effective_signal == 'SELL':
        action_intent = 'EXIT'

    confidence = _safe_float(model.get('confidence'))
    buy_threshold = _safe_float(getattr(settings, 'ai_buy_threshold', None))
    sell_threshold = _safe_float(getattr(settings, 'ai_sell_threshold', None))
    hold_band_low = _safe_float(getattr(settings, 'ai_hold_band_low', None))
    hold_band_high = _safe_float(getattr(settings, 'ai_hold_band_high', None))
    indecision_margin = _safe_float(getattr(settings, 'ai_indecision_margin', None))

    calibration_reason = _metric(metrics, 'calibrationReason', 'calibration_reason')
    raw_predicted_class = _metric(metrics, 'rawPredictedClass', 'raw_predicted_class')
    calibrated_class = _metric(metrics, 'calibratedClass', 'calibrated_class')
    raw_margin = _safe_float(_metric(metrics, 'rawMargin', 'raw_margin'))

    reason_codes: list[str] = []
    if raw_signal == 'HOLD':
        reason_codes.append('RAW_SIGNAL_HOLD')
    if effective_signal == 'HOLD':
        reason_codes.append('EFFECTIVE_SIGNAL_HOLD')
    if calibration_reason:
        reason_codes.append(str(calibration_reason))
    if skip_code:
        reason_codes.append(str(skip_code))
    if should_submit_order:
        reason_codes.append('ORDER_SUBMISSION_INTENDED')
    if action == 'AUTO_DISABLED':
        reason_codes.append('AUTO_TRADE_DISABLED')
    if action == 'AUTO_SIGNAL_DEDUPED':
        reason_codes.append('SIGNAL_DEDUPED')

    has_pending = getattr(runtime, 'pending', None) is not None
    has_position = getattr(runtime, 'position', None) is not None
    runtime_state = str(getattr(runtime, 'state', 'UNKNOWN'))

    guard_path = {
        'runtime_state': runtime_state,
        'has_pending': has_pending,
        'has_position': has_position,
        'auto_trade_on_signal': bool(getattr(settings, 'auto_trade_on_signal', False)),
        'signal_mode': getattr(settings, 'auto_trade_signal_mode', 'normal'),
        'action': action,
        'action_intent': action_intent,
        'should_submit_order': bool(should_submit_order),
        'skip_code': skip_code,
        'signal_key': signal_key,
    }

    technical_metrics = {
        'ema_fast': _safe_float(_metric(metrics, 'emaFast', 'ema_fast')),
        'ema_slow': _safe_float(_metric(metrics, 'emaSlow', 'ema_slow')),
        'prev_ema_fast': _safe_float(_metric(metrics, 'prevEmaFast', 'prev_ema_fast')),
        'prev_ema_slow': _safe_float(_metric(metrics, 'prevEmaSlow', 'prev_ema_slow')),
        'rsi': _safe_float(_metric(metrics, 'rsi')),
        'atr': _safe_float(_metric(metrics, 'atr')),
        'volume_ratio': _safe_float(_metric(metrics, 'volumeRatio', 'volume_ratio')),
        'quote_volume_avg': _safe_float(_metric(metrics, 'quoteVolumeAvg', 'quote_volume_avg')),
        'signal_quote_volume': _safe_float(_metric(metrics, 'signalQuoteVolume', 'signal_quote_volume')),
        'taker_buy_pressure': _safe_float(_metric(metrics, 'takerBuyPressure', 'taker_buy_pressure')),
    }

    threshold_trace = {
        'confidence': confidence,
        'buy_threshold': buy_threshold,
        'sell_threshold': sell_threshold,
        'hold_band_low': hold_band_low,
        'hold_band_high': hold_band_high,
        'indecision_margin': indecision_margin,
        'raw_margin': raw_margin,
        'raw_predicted_class': raw_predicted_class,
        'calibrated_class': calibrated_class,
        'calibration_reason': calibration_reason,
    }

    explainability_notes: list[str] = []
    explainability_notes.append(f"technical={technical.get('signal')} trend={technical.get('trend')}")
    explainability_notes.append(f"model={model.get('signal')} provider={model.get('provider')}")
    explainability_notes.append(f"effective={effective_signal} action={action}")
    if calibration_reason:
        explainability_notes.append(f"calibration={calibration_reason}")
    if skip_code:
        explainability_notes.append(f"guard={skip_code}")

    return {
        'contract_version': DECISION_AUDIT_CONTRACT_VERSION,
        'generated_at': int(now),
        'symbol': symbol,
        'interval': interval,
        'close_time': model.get('last_evaluated_close_time') or technical.get('last_evaluated_close_time'),
        'raw_decision': model,
        'technical_decision': technical,
        'effective_decision': effective,
        'technical': {
            'signal': _metric(metrics, 'technicalSignal') or technical.get('signal'),
            'trend': _metric(metrics, 'technicalTrend') or technical.get('trend'),
            'reason': _metric(metrics, 'technicalReason') or technical.get('reason'),
            'metrics': technical_metrics,
        },
        'ai': {
            'enabled': bool(getattr(settings, 'ai_provider_enabled', False)),
            'mode': getattr(settings, 'ai_provider_mode', 'disabled'),
            'provider': model.get('provider'),
            'confidence': confidence,
            'buy_probability': _safe_float(_metric(metrics, 'buyProbability', 'buy_probability')),
            'sell_probability': _safe_float(_metric(metrics, 'sellProbability', 'sell_probability')),
            'hold_probability': _safe_float(_metric(metrics, 'holdProbability', 'hold_probability')),
            'raw_top_probability': _safe_float(_metric(metrics, 'rawTopProbability', 'raw_top_probability')),
            'raw_predicted_class': raw_predicted_class,
            'calibrated_class': calibrated_class,
            'calibration_reason': calibration_reason,
        },
        'threshold_trace': threshold_trace,
        'guard_path': guard_path,
        'action': action,
        'action_intent': action_intent,
        'should_submit_order': bool(should_submit_order),
        'skip_code': skip_code,
        'signal_key': signal_key,
        'reason_codes': list(dict.fromkeys(reason_codes)),
        'explainability_notes': explainability_notes,
    }


def empty_decision_audit_snapshot(*, now: int, symbol: str, interval: str) -> dict[str, Any]:
    return {
        'contract_version': DECISION_AUDIT_CONTRACT_VERSION,
        'generated_at': int(now),
        'symbol': symbol,
        'interval': interval,
        'close_time': None,
        'raw_decision': {'signal': 'HOLD', 'trend': 'UNKNOWN', 'reason': 'Henüz değerlendirme yok', 'provider': None, 'confidence': None, 'last_evaluated_close_time': None},
        'technical_decision': {'signal': 'HOLD', 'trend': 'UNKNOWN', 'reason': 'Henüz değerlendirme yok', 'provider': None, 'confidence': None, 'last_evaluated_close_time': None},
        'effective_decision': {'signal': 'HOLD', 'trend': 'UNKNOWN', 'reason': 'Henüz değerlendirme yok', 'provider': None, 'confidence': None, 'last_evaluated_close_time': None},
        'technical': {'signal': 'HOLD', 'trend': 'UNKNOWN', 'reason': 'Henüz değerlendirme yok', 'metrics': {}},
        'ai': {'enabled': False, 'mode': 'disabled', 'provider': None, 'confidence': None},
        'threshold_trace': {},
        'guard_path': {'runtime_state': 'UNKNOWN', 'has_pending': False, 'has_position': False, 'auto_trade_on_signal': False, 'signal_mode': 'normal', 'action': 'NO_DATA', 'action_intent': 'NONE', 'should_submit_order': False, 'skip_code': None, 'signal_key': None},
        'action': 'NO_DATA',
        'action_intent': 'NONE',
        'should_submit_order': False,
        'skip_code': None,
        'signal_key': None,
        'reason_codes': ['NO_DECISION_YET'],
        'explainability_notes': ['Henüz strateji kararı yok.'],
    }
