from __future__ import annotations

from collections import Counter
from typing import Any

SENSITIVE_TOKENS = ('api_key', 'apikey', 'api_secret', 'secret', 'signature', 'x-mbx-apikey')

CATEGORY_PREFIXES: tuple[tuple[str, str], ...] = (
    ('ORDER_', 'Orders'), ('LIVE_PREFLIGHT', 'Orders'), ('POSITION_', 'Positions'),
    ('AUTO_ENTRY', 'Signals'), ('AUTO_EXIT', 'Signals'), ('AUTO_SIGNAL', 'Signals'), ('STRATEGY_', 'Signals'),
    ('AI_', 'Model'), ('MODEL_', 'Model'), ('TRAIN_', 'Model'),
    ('RECONCILE', 'Reconcile'), ('PENDING_', 'Reconcile'),
    ('SAFE_MODE', 'Risk'), ('RISK_', 'Risk'), ('DAILY_', 'Risk'), ('CONSECUTIVE_', 'Risk'),
    ('BALANCES_', 'Account'), ('SYMBOL_RULES', 'Account'), ('ACCOUNT_', 'Account'),
    ('WS_', 'Runtime'), ('STATE_', 'Runtime'), ('BOOTSTRAP_', 'Runtime'), ('SESSION_', 'Runtime'), ('STARTUP_', 'Runtime'),
    ('OPERATOR_', 'Operator'),
)

CATEGORY_BY_CODE: dict[str, str] = {
    'ORDER_SUBMITTED': 'Orders', 'ORDER_FILLED': 'Orders', 'ORDER_CANCEL_REQUESTED': 'Orders',
    'ORDER_CANCEL_SUPPRESSED': 'Orders', 'ORDER_CANCEL_RACE_FILLED': 'Orders', 'ORDER_CANCEL_WARN': 'Orders',
    'ENTRY_BLOCKED': 'Guards', 'EXIT_BLOCKED': 'Guards', 'ENTRY_ALREADY_PENDING': 'Guards',
    'EXIT_ALREADY_PENDING': 'Guards', 'AUTO_ENTRY_BLOCKED': 'Guards', 'AUTO_EXIT_BLOCKED': 'Guards',
    'MIN_NOTIONAL_BLOCKED': 'Guards', 'MIN_QTY_BLOCKED': 'Guards', 'INSUFFICIENT_QUOTE_BALANCE': 'Guards',
    'MAX_CONSECUTIVE_LOSSES_REACHED': 'Guards', 'DAILY_LOSS_LIMIT_REACHED': 'Guards',
    'STARTUP_HYGIENE_APPLIED': 'Runtime', 'SESSION_DAY_ROLLED': 'Runtime',
    'AI_RELOAD_REQUESTED': 'Model', 'AI_RELOAD_SUCCEEDED': 'Model', 'AI_RELOAD_FAILED': 'Model',
    'AI_TRAIN_REQUESTED': 'Model', 'AI_TRAIN_SUCCEEDED': 'Model', 'AI_TRAIN_FAILED': 'Model',
}


def _safe_str(value: Any, *, max_len: int = 800) -> str:
    text = str(value)
    return text[: max_len - 3] + '...' if len(text) > max_len else text


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            lower = key_str.lower().replace('-', '_')
            out[key_str] = '[REDACTED]' if any(token in lower for token in SENSITIVE_TOKENS) else redact_sensitive(item)
        return out
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _safe_str(value)


def audit_category(code: str, data: dict[str, Any] | None = None) -> str:
    code_u = str(code or '').upper()
    if code_u in CATEGORY_BY_CODE:
        return CATEGORY_BY_CODE[code_u]
    for prefix, category in CATEGORY_PREFIXES:
        if code_u.startswith(prefix):
            return category
    if code_u.endswith('_BLOCKED') or code_u.endswith('_LOCKED') or 'GUARD' in code_u:
        return 'Guards'
    if 'RELOAD' in code_u or 'SCHEMA' in code_u:
        return 'Model'
    return 'Runtime'


def audit_severity(level: str, code: str, data: dict[str, Any] | None = None) -> str:
    level_u = str(level or '').upper()
    code_u = str(code or '').upper()
    if level_u in {'ERROR', 'CRITICAL'} or code_u.endswith('_FAIL') or code_u.endswith('_FAILED'):
        return 'error'
    if level_u in {'WARN', 'WARNING'} or 'BLOCKED' in code_u or 'LOCKED' in code_u or 'MISMATCH' in code_u or 'ANOMALY' in code_u or code_u in {'SAFE_MODE_AUTO_ENABLED', 'SAFE_MODE_MANUAL_ENABLED', 'ORDER_CANCEL_WARN'}:
        return 'warning'
    return 'info'


def audit_correlation_id(code: str, data: dict[str, Any] | None = None) -> str | None:
    data = data or {}
    for key in ('clientOrderId', 'client_order_id', 'orderId', 'order_id', 'signalKey', 'signal_key', 'correlationId', 'correlation_id'):
        value = data.get(key)
        if value not in (None, ''):
            return str(value)
    symbol = data.get('symbol') or data.get('baseAsset') or data.get('quoteAsset')
    side = data.get('side') or data.get('action')
    if symbol and side:
        return f'{symbol}:{side}'
    return None


def normalize_audit_event(event: dict[str, Any]) -> dict[str, Any]:
    raw_data = event.get('data') or {}
    data = redact_sensitive(raw_data if isinstance(raw_data, dict) else {'value': raw_data})
    code = str(event.get('code') or '-')
    level = str(event.get('level') or 'INFO').upper()
    category = event.get('category') or audit_category(code, data if isinstance(data, dict) else {})
    severity = event.get('severity') or audit_severity(level, code, data if isinstance(data, dict) else {})
    normalized = dict(event)
    normalized.update({
        'level': level,
        'code': code,
        'message': str(event.get('message') or '-'),
        'data': data,
        'category': category,
        'severity': severity,
        'correlation_id': event.get('correlation_id') or audit_correlation_id(code, data if isinstance(data, dict) else {}),
    })
    return normalized


def summarize_audit_events(events: list[dict[str, Any]], *, recent_limit: int = 10) -> dict[str, Any]:
    normalized = [normalize_audit_event(event) for event in events]
    by_category = Counter(str(event.get('category') or 'Runtime') for event in normalized)
    by_severity = Counter(str(event.get('severity') or 'info') for event in normalized)
    errors = [event for event in normalized if event.get('severity') == 'error']
    warnings = [event for event in normalized if event.get('severity') == 'warning']
    latest_ts = max((int(event.get('ts') or 0) for event in normalized), default=None)
    recent = normalized[-recent_limit:] if recent_limit > 0 else normalized
    return {
        'event_count': len(normalized),
        'latest_ts': latest_ts,
        'counts_by_category': dict(sorted(by_category.items())),
        'counts_by_severity': dict(sorted(by_severity.items())),
        'warning_count': len(warnings),
        'error_count': len(errors),
        'last_warning': warnings[-1] if warnings else None,
        'last_error': errors[-1] if errors else None,
        'recent': recent,
    }
