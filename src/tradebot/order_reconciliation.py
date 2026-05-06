from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ORDER_RECONCILIATION_CONTRACT_VERSION = '4B.4.3.6.6.18'


@dataclass(slots=True)
class ReconciliationConfig:
    base_backoff_ms: int = 1_000
    max_backoff_ms: int = 15_000
    missing_warning_count: int = 2
    missing_critical_count: int = 3
    max_attempts_before_deferred: int = 8
    late_fill_grace_ms: int = 30_000


def config_from_settings(settings: Any) -> ReconciliationConfig:
    order_timeout_sec = int(getattr(settings, 'order_timeout_sec', 20) or 20)
    return ReconciliationConfig(
        base_backoff_ms=int(getattr(settings, 'reconciliation_base_backoff_ms', 1_000) or 1_000),
        max_backoff_ms=int(getattr(settings, 'reconciliation_max_backoff_ms', 15_000) or 15_000),
        missing_warning_count=int(getattr(settings, 'reconciliation_missing_warning_count', 2) or 2),
        missing_critical_count=int(getattr(settings, 'reconciliation_missing_critical_count', 3) or 3),
        max_attempts_before_deferred=int(getattr(settings, 'reconciliation_max_attempts_before_deferred', max(8, order_timeout_sec // 2)) or max(8, order_timeout_sec // 2)),
        late_fill_grace_ms=int(getattr(settings, 'reconciliation_late_fill_grace_ms', 30_000) or 30_000),
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _order_matches(order: dict[str, Any], order_id: str | None, client_order_id: str | None) -> bool:
    if not order:
        return False
    live_order_id = order.get('orderId')
    live_client_id = order.get('clientOrderId')
    if order_id is not None and live_order_id is not None and str(live_order_id) == str(order_id):
        return True
    if client_order_id and live_client_id and str(live_client_id) == str(client_order_id):
        return True
    return False


def _find_open_order(open_orders: list[dict[str, Any]] | None, order_id: str | None, client_order_id: str | None) -> dict[str, Any] | None:
    for order in open_orders or []:
        if _order_matches(order, order_id, client_order_id):
            return order
    return None


def _next_retry_after_ms(attempts: int, cfg: ReconciliationConfig) -> int:
    attempts = max(int(attempts or 0), 0)
    value = cfg.base_backoff_ms * (2 ** min(attempts, 5))
    return max(cfg.base_backoff_ms, min(value, cfg.max_backoff_ms))


def build_reconciliation_snapshot(
    *,
    pending: Any | None,
    now: int,
    symbol: str,
    settings: Any | None = None,
    order: dict[str, Any] | None = None,
    open_orders: list[dict[str, Any]] | None = None,
    phase: str = 'OBSERVE',
    action: str = 'WAIT',
    reason: str | None = None,
    error: str | None = None,
    fill_source: str | None = None,
) -> dict[str, Any]:
    cfg = config_from_settings(settings)
    if pending is None:
        return {
            'contract_version': ORDER_RECONCILIATION_CONTRACT_VERSION,
            'generated_at': now,
            'symbol': symbol,
            'pending_present': False,
            'state': 'IDLE',
            'phase': phase,
            'recommended_action': 'NONE',
            'reason_codes': [],
            'warnings': [],
        }

    order_id = _get(pending, 'order_id')
    client_order_id = _get(pending, 'client_order_id')
    side = str(_get(pending, 'side', '') or '').upper()
    qty = _safe_float(_get(pending, 'qty'), 0.0)
    submitted_at = _safe_int(_get(pending, 'submitted_at'), 0)
    attempts = _safe_int(_get(pending, 'reconcile_attempts'), 0)
    missing_count = _safe_int(_get(pending, 'missing_count'), 0)
    cancel_requested = bool(_get(pending, 'cancel_requested', False))
    deferred = bool(_get(pending, 'deferred', False))
    age_ms = max(0, now - submitted_at) if submitted_at else 0
    matched_open_order = _find_open_order(open_orders, order_id, client_order_id)
    open_order_present = matched_open_order is not None

    live_status = str((order or {}).get('status') or _get(pending, 'status', 'UNKNOWN') or 'UNKNOWN')
    live_executed_qty = _safe_float((order or {}).get('executedQty'), _safe_float(_get(pending, 'partial_executed_qty'), 0.0))
    live_orig_qty = _safe_float((order or {}).get('origQty'), qty)
    live_remaining_qty = max(live_orig_qty - live_executed_qty, 0.0)
    fill_ratio = (live_executed_qty / live_orig_qty) if live_orig_qty > 0 else 0.0

    reason_codes: list[str] = []
    warnings: list[str] = []
    state = 'TRACKING'
    recommended_action = action or 'WAIT'
    severity = 'ok'

    if error:
        state = 'ERROR'
        severity = 'warning'
        reason_codes.append('RECONCILE_FETCH_ERROR')
        warnings.append(error)
        recommended_action = 'POLL_AGAIN'
    elif live_status == 'FILLED' or fill_ratio >= 0.999:
        state = 'FILLED'
        reason_codes.append('LIVE_ORDER_FILLED')
        recommended_action = 'COMMIT_FILL'
    elif live_status == 'PARTIALLY_FILLED' or live_executed_qty > 0:
        state = 'PARTIAL_FILL'
        reason_codes.append('LIVE_ORDER_PARTIAL_FILL')
        recommended_action = 'POLL_AGAIN'
    elif live_status in {'CANCELED', 'EXPIRED', 'REJECTED'}:
        state = 'TERMINAL_CANCELED'
        reason_codes.append(f'LIVE_ORDER_{live_status}')
        recommended_action = 'CLEAR_PENDING'
    elif cancel_requested:
        state = 'CANCEL_REQUESTED'
        reason_codes.append('CANCEL_REQUESTED')
        recommended_action = 'WAIT_CANCEL_CONFIRMATION'
    elif deferred:
        state = 'DEFERRED'
        severity = 'warning'
        reason_codes.append('RECONCILIATION_DEFERRED')
        recommended_action = 'REQUEST_CANCEL' if open_order_present else 'POLL_AGAIN'
    elif order is None and not open_order_present and missing_count >= cfg.missing_critical_count:
        state = 'ORPHAN_MISSING'
        severity = 'critical'
        reason_codes.append('LIVE_ORDER_MISSING_CRITICAL')
        recommended_action = 'CLEAR_PENDING'
    elif order is None and not open_order_present and missing_count >= cfg.missing_warning_count:
        state = 'MISSING_WARNING'
        severity = 'warning'
        reason_codes.append('LIVE_ORDER_MISSING_WARNING')
        recommended_action = 'POLL_AGAIN'

    if attempts >= cfg.max_attempts_before_deferred and state == 'TRACKING':
        state = 'DEFER_CANDIDATE'
        severity = 'warning'
        reason_codes.append('MAX_RECONCILE_ATTEMPTS_REACHED')
        recommended_action = 'REQUEST_CANCEL' if open_order_present else 'POLL_AGAIN'

    if reason:
        reason_codes.append(reason)

    return {
        'contract_version': ORDER_RECONCILIATION_CONTRACT_VERSION,
        'generated_at': now,
        'symbol': symbol,
        'pending_present': True,
        'state': state,
        'severity': severity,
        'phase': phase,
        'recommended_action': recommended_action,
        'reason_codes': reason_codes,
        'warnings': warnings,
        'order_id': order_id,
        'client_order_id': client_order_id,
        'side': side,
        'source': _get(pending, 'source'),
        'submitted_at': submitted_at,
        'age_ms': age_ms,
        'attempts': attempts,
        'missing_count': missing_count,
        'cancel_requested': cancel_requested,
        'cancel_requested_at': _get(pending, 'cancel_requested_at'),
        'deferred': deferred,
        'pending_status': _get(pending, 'status'),
        'live_order_status': live_status,
        'open_order_present': open_order_present,
        'live_executed_qty': live_executed_qty,
        'live_remaining_qty': live_remaining_qty,
        'fill_ratio': round(fill_ratio, 8),
        'partial_fill': live_executed_qty > 0 and fill_ratio < 0.999,
        'requested_qty': qty,
        'remaining_qty': _safe_float(_get(pending, 'remaining_qty'), live_remaining_qty),
        'next_retry_after_ms': _next_retry_after_ms(attempts, cfg),
        'fill_source': fill_source,
        'last_error': error,
    }
