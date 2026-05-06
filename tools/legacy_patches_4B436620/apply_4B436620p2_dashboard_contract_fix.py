from __future__ import annotations

from pathlib import Path
import re

START = "# BEGIN 4B.4.3.6.6.20P2 DASHBOARD CONTRACT FIX"
END = "# END 4B.4.3.6.6.20P2 DASHBOARD CONTRACT FIX"

COMPAT_BLOCK = r'''
# BEGIN 4B.4.3.6.6.20P2 DASHBOARD CONTRACT FIX
import ast as _p2_ast
import json as _p2_json
from urllib.parse import urlencode as _p2_urlencode
from typing import Any as _P2Any

AUDIT_VIEWER_CONTRACT_VERSION = '4B.4.3.6.6.20'
DASHBOARD_CONTROL_CONTRACT_VERSION = '4B.4.3.6.6.20'


def _p2_dict(value: _P2Any) -> dict[str, _P2Any]:
    return value if isinstance(value, dict) else {}


def _p2_list(value: _P2Any) -> list[_P2Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _p2_bool(value: _P2Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on', 'enabled', 'ready', 'normal'}
    return bool(value)


def _p2_float(value: _P2Any, default: float = 0.0) -> float:
    try:
        if value is None or value == '':
            return default
        return float(value)
    except Exception:
        return default


def _p2_int(value: _P2Any, default: int = 0) -> int:
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except Exception:
        return default


def _p2_fmt(value: _P2Any, digits: int = 4) -> str:
    try:
        if value is None:
            return '-'
        return f'{float(value):.{int(digits)}f}'
    except Exception:
        return '-' if value in (None, '') else str(value)


def _p2_is_all(value: _P2Any) -> bool:
    if value is None:
        return True
    return str(value).strip() in {'', '-', 'All', 'ALL', 'all', 'Tümü', 'TUMU', 'Tümü / All'}


def _p2_norm_level(value: _P2Any) -> str:
    raw = str(value or '').strip().upper()
    return 'WARN' if raw == 'WARNING' else raw


def _p2_getattr(obj: object, name: str, default: _P2Any = None) -> _P2Any:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


def _p2_var_value(obj: _P2Any, default: _P2Any = None) -> _P2Any:
    try:
        if hasattr(obj, 'get') and callable(obj.get):
            return obj.get()
    except Exception:
        pass
    return default


def _p2_cfg(widget: _P2Any, **kwargs: _P2Any) -> None:
    if widget is None:
        return
    try:
        widget.configure(**kwargs)
    except Exception:
        pass
    try:
        existing = _p2_getattr(widget, 'kwargs', None)
        if isinstance(existing, dict):
            existing.update(kwargs)
    except Exception:
        pass
    for key, value in kwargs.items():
        try:
            setattr(widget, key, value)
        except Exception:
            pass


def _p2_direct_set(widget: _P2Any, text: str) -> None:
    if widget is None:
        return
    try:
        setattr(widget, 'text', text)
    except Exception:
        pass
    try:
        existing = _p2_getattr(widget, 'kwargs', None)
        if isinstance(existing, dict):
            existing['text'] = text
    except Exception:
        pass
    try:
        widget.delete('1.0', 'end')
        widget.insert('end', text)
    except Exception:
        try:
            widget.delete(0, 'end')
            widget.insert(0, text)
        except Exception:
            pass
    _p2_cfg(widget, text=text)


def _p2_target_attr(target: _P2Any) -> str | None:
    if not isinstance(target, str):
        return None
    aliases = {
        'status-box': 'status_box', 'risk-box': 'risk_box', 'position-box': 'position_box',
        'ai-box': 'ai_box', 'pending-box': 'pending_box', 'log-box': 'log_box',
        'event-box': 'event_box', 'audit-box': 'audit_box', 'audit-summary-box': 'audit_summary_box',
        'backend-box': 'backend_box', 'session-summary-box': 'session_summary_box',
    }
    return aliases.get(target, target.replace('-', '_'))


def _p2_set_text(app: _P2Any, target: _P2Any, text: str) -> None:
    setter = _p2_getattr(app, '_set_text', None)
    if callable(setter):
        try:
            setter(target, text)
        except Exception:
            pass
    if isinstance(target, str):
        attr = _p2_target_attr(target)
        _p2_direct_set(_p2_getattr(app, attr, None), text)
    else:
        _p2_direct_set(target, text)


def _p2_position(status: dict[str, _P2Any]) -> dict[str, _P2Any]:
    return _p2_dict(status.get('position_snapshot') or status.get('position') or {})


def _p2_pending(status: dict[str, _P2Any]) -> dict[str, _P2Any]:
    return _p2_dict(status.get('pending_snapshot') or status.get('pending') or {})


def _p2_position_present(status: dict[str, _P2Any]) -> bool:
    position = _p2_position(status)
    return _p2_bool(position.get('present')) or _p2_float(position.get('qty'), 0.0) > 0 or str(status.get('state', '')).upper() == 'IN_POSITION'


def _p2_pending_present(status: dict[str, _P2Any]) -> bool:
    pending = _p2_pending(status)
    state = str(status.get('state', '')).upper()
    return _p2_bool(pending.get('present')) or state in {'BUY_PENDING', 'SELL_PENDING'} or state.endswith('_PENDING')


def _p2_contract_ok(version: _P2Any) -> bool:
    raw = str(version or '')
    if not raw:
        return True
    if not raw.startswith('4B.4.3.6.6.'):
        return False
    try:
        return int(raw.rsplit('.', 1)[-1]) >= 7
    except Exception:
        return True


def _p2_health_reason_codes(health: dict[str, _P2Any]) -> list[str]:
    codes: list[str] = []
    pairs = [
        ('account_consistency', 'ACCOUNT_CONSISTENCY_BROKEN'),
        ('position_consistency', 'POSITION_CONSISTENCY_BROKEN'),
        ('pending_consistency', 'PENDING_CONSISTENCY_BROKEN'),
    ]
    for key, code in pairs:
        raw = str(health.get(key, 'HEALTHY') or 'HEALTHY').upper()
        if raw not in {'HEALTHY', 'OK', 'TRUE', 'CONNECTED', '-'}:
            codes.append(code)
    anomaly = health.get('active_anomaly_code')
    if anomaly:
        codes.append(str(anomaly))
    return codes


def _p2_protective_reason(status: dict[str, _P2Any]) -> str | None:
    if not _p2_position_present(status):
        return None
    protective = _p2_dict(_p2_position(status).get('protective_exit'))
    if not protective:
        return None
    block = protective.get('block_reason')
    ready = protective.get('protective_exit_ready')
    if block and str(block).upper() not in {'-', 'NONE', 'OK', ''}:
        return f'PROTECTIVE_EXIT_BLOCKED:{str(block).upper()}'
    if ready is False:
        return 'PROTECTIVE_EXIT_BLOCKED'
    return None


def build_operator_control_state(status: dict[str, _P2Any] | None = None, *, connected: bool = True, **_: _P2Any) -> dict[str, _P2Any]:
    status = _p2_dict(status)
    health = _p2_dict(status.get('health_snapshot'))
    risk = _p2_dict(status.get('risk_snapshot') or status)
    state = str(status.get('state') or status.get('runtime_state') or 'UNKNOWN')
    state_upper = state.upper()
    pending = _p2_pending_present(status)
    position = _p2_position_present(status)
    safe_mode = _p2_bool(risk.get('safe_mode') or status.get('safe_mode'))
    kill_switch = _p2_bool(risk.get('kill_switch_active') or status.get('kill_switch_active'))
    health_reasons = _p2_health_reason_codes(health)
    health_ok = not health_reasons
    contract_ok = _p2_contract_ok(status.get('contract_version'))
    protective_reason = _p2_protective_reason(status)

    reason_codes: list[str] = []
    if not connected:
        reason_codes.append('BACKEND_OFFLINE')
    if not contract_ok:
        reason_codes.append('STATUS_CONTRACT_STALE')
    reason_codes.extend(health_reasons)
    if kill_switch:
        reason_codes.append('KILL_SWITCH_ACTIVE')
    if pending:
        reason_codes.append('PENDING_ORDER_ACTIVE')
    if safe_mode:
        reason_codes.append('SAFE_MODE_ACTIVE')
    if position:
        reason_codes.append('POSITION_ACTIVE')
    if protective_reason:
        reason_codes.append(protective_reason)

    force_buy = bool(connected and contract_ok and health_ok and not kill_switch and not pending and not position and not safe_mode)
    force_sell = bool(connected and contract_ok and health_ok and not kill_switch and position and not pending and not protective_reason)
    cancel_pending = bool(connected and pending)
    start = bool(connected and not _p2_bool(status.get('running', True)))
    stop = bool(connected and _p2_bool(status.get('running', True)))

    if not connected or kill_switch or not health_ok or not contract_ok:
        severity = 'danger'
    elif pending:
        severity = 'busy'
    elif safe_mode:
        severity = 'safe'
    elif position:
        severity = 'position'
    else:
        severity = 'ready'

    if pending:
        hint = 'PENDING_ORDER_ACTIVE'
    elif protective_reason:
        hint = protective_reason
    elif force_buy:
        hint = 'Force BUY ready'
    elif force_sell:
        hint = 'Force SELL ready'
    elif safe_mode:
        hint = 'SAFE_MODE_ACTIVE'
    elif not health_ok:
        hint = ','.join(health_reasons)
    elif not contract_ok:
        hint = 'STATUS_CONTRACT_STALE'
    else:
        hint = ','.join(reason_codes) or 'READY'

    buttons = {
        'force_buy': force_buy, 'force_sell': force_sell, 'cancel_pending': cancel_pending,
        'safe_mode': bool(connected), 'safe_mode_toggle': bool(connected), 'balance_sync': bool(connected),
        'ai_reload': bool(connected), 'start': start, 'stop': stop,
    }
    return {
        'contract_version': DASHBOARD_CONTROL_CONTRACT_VERSION,
        'connected': bool(connected), 'state': state, 'health_ok': health_ok, 'contract_ok': contract_ok,
        'safe_mode': safe_mode, 'kill_switch_active': kill_switch, 'has_pending': pending, 'has_position': position,
        'protective_exit_ready': protective_reason is None if position else False,
        'severity': severity, 'warnings': [c for c in reason_codes if c not in {'POSITION_ACTIVE'}],
        'reason_codes': list(dict.fromkeys(reason_codes)), 'hint': hint,
        'force_buy': force_buy, 'force_sell': force_sell, 'cancel_pending': cancel_pending,
        'start': start, 'stop': stop, 'buttons': buttons,
    }


def _p2_take_profit(position: dict[str, _P2Any], risk_plan: dict[str, _P2Any], protective: dict[str, _P2Any]) -> _P2Any:
    return protective.get('take_profit') or risk_plan.get('take_profit') or risk_plan.get('tp')


def build_position_management_text(status_or_position: dict[str, _P2Any] | None = None) -> str:
    payload = _p2_dict(status_or_position)
    position = _p2_dict(payload.get('position_snapshot') or payload.get('position') or payload)
    protective = _p2_dict(position.get('protective_exit'))
    risk_plan = _p2_dict(position.get('risk_plan'))
    risk_exec = _p2_dict(protective.get('risk_execution') or position.get('risk_execution'))
    present = _p2_bool(position.get('present')) or _p2_float(position.get('qty'), 0.0) > 0
    ready = _p2_bool(protective.get('protective_exit_ready'))
    if present and not protective:
        ready = True
    block = protective.get('block_reason') or '-'
    eff_sl = risk_exec.get('effective_stop_loss') or protective.get('effective_stop_loss') or risk_plan.get('active_stop_loss') or risk_plan.get('stop_loss')
    stop = protective.get('stop_loss') or risk_plan.get('stop_loss')
    take = _p2_take_profit(position, risk_plan, protective)
    partial_done = risk_plan.get('partial_tp_done', risk_plan.get('partial_tp_hit', risk_exec.get('partial_tp_done', False)))
    exec_status = risk_exec.get('status') or ('READY' if present else 'BLOCKED')
    exec_signal = risk_exec.get('exit_signal') or risk_exec.get('exit_action') or 'HOLD'
    lines = [
        f"Position status : {'IN_POSITION' if present else 'FLAT'}",
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_p2_fmt(position.get('qty'), 8)}",
        f"Entry           : {_p2_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_p2_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_p2_fmt(position.get('unrealized_pnl'), 6)}",
        f"Protective exit : {'READY' if ready else 'BLOCKED'} / {block}",
        f"Exit qty        : {_p2_fmt(protective.get('tradable_exit_qty'), 8)}",
        f"Exit notional   : {_p2_fmt(protective.get('exit_notional'), 4)}",
        f"Dust position   : {'YES' if _p2_bool(protective.get('is_dust')) else 'NO'}",
        f"Risk plan       : {'READY' if risk_plan or present else 'MISSING'}",
        f"Stop loss       : {_p2_fmt(stop, 4)}",
        f"Effective SL    : {_p2_fmt(eff_sl, 4)}",
        f"Take profit     : {_p2_fmt(take, 4)}",
        f"Partial TP done : {bool(partial_done)}",
        f"Risk exec       : {exec_status} / {exec_signal}",
    ]
    return '\n'.join(lines)


def _p2_event_category(item: dict[str, _P2Any]) -> str:
    raw = item.get('category')
    if raw and not _p2_is_all(raw):
        return str(raw)
    level = _p2_norm_level(item.get('level'))
    code = str(item.get('code') or '').upper()
    if level in {'WARN', 'ERROR', 'CRITICAL'}:
        return 'Warnings'
    if code.startswith(('ORDER_', 'LIVE_', 'FILL_', 'ENTRY_ORDER', 'EXIT_ORDER')):
        return 'Orders'
    if code.startswith(('AUTO_', 'GUARD_', 'ENTRY_GUARD', 'EXIT_GUARD')):
        return 'Guards'
    if code.startswith(('RISK_', 'SAFE_', 'KILL_')):
        return 'Risk'
    if code.startswith(('AI_', 'MODEL_', 'STRATEGY_')):
        return 'AI'
    return 'System'


def _p2_event_severity(item: dict[str, _P2Any]) -> str:
    raw = item.get('severity')
    if raw and not _p2_is_all(raw):
        return str(raw).lower()
    level = _p2_norm_level(item.get('level'))
    if level in {'ERROR', 'CRITICAL'}:
        return 'error'
    if level == 'WARN':
        return 'warning'
    return 'info'


def _p2_corr(item: dict[str, _P2Any]) -> str:
    data = _p2_dict(item.get('data'))
    for key in ('correlation_id', 'correlationId', 'clientOrderId', 'client_order_id', 'orderId', 'order_id'):
        if item.get(key):
            return str(item.get(key))
        if data.get(key):
            return str(data.get(key))
    return '-'


def _p2_blob(item: dict[str, _P2Any]) -> str:
    return ' '.join([str(item.get('level') or ''), str(item.get('code') or ''), str(item.get('message') or ''), _p2_event_category(item), _p2_event_severity(item), _p2_corr(item), _p2_json.dumps(item.get('data') or {}, ensure_ascii=False, sort_keys=True)]).lower()


def format_log_line(item: dict[str, _P2Any]) -> str:
    item = _p2_dict(item)
    return f"{_p2_norm_level(item.get('level') or 'INFO')} | {_p2_event_category(item)} | {_p2_event_severity(item)} | {item.get('code') or '-'} | corr={_p2_corr(item)} | {item.get('message') or ''}"


def build_audit_query_path(*, limit: int = 50, order: str = 'desc', level: _P2Any = None, code: _P2Any = None, code_prefix: _P2Any = None, contains: _P2Any = None, q: _P2Any = None, category: _P2Any = None, severity: _P2Any = None, correlation: _P2Any = None, **extra: _P2Any) -> str:
    params: dict[str, _P2Any] = {'limit': int(limit), 'order': str(order or 'desc').lower()}
    if not _p2_is_all(level): params['level'] = _p2_norm_level(level)
    if not _p2_is_all(code): params['code'] = str(code).upper()
    if not _p2_is_all(code_prefix): params['code_prefix'] = str(code_prefix).upper()
    if not _p2_is_all(category): params['category'] = str(category)
    if not _p2_is_all(severity): params['severity'] = str(severity).lower()
    if not _p2_is_all(correlation): params['correlation'] = str(correlation)
    query = q if not _p2_is_all(q) else contains
    if not _p2_is_all(query): params['q'] = str(query)
    for key in ('since_ts', 'until_ts', 'offset', 'cursor'):
        if key in extra and extra[key] not in (None, ''):
            params[key] = extra[key]
    return '/events/audit?' + _p2_urlencode(params)


def filter_audit_events(events: _P2Any, filters: dict[str, _P2Any] | None = None, **kwargs: _P2Any) -> list[dict[str, _P2Any]]:
    merged = dict(filters or {})
    merged.update({k: v for k, v in kwargs.items() if v is not None})
    filtered = [dict(item) for item in _p2_list(events) if isinstance(item, dict)]
    if not _p2_is_all(merged.get('level')):
        filtered = [i for i in filtered if _p2_norm_level(i.get('level')) == _p2_norm_level(merged.get('level'))]
    if not _p2_is_all(merged.get('code')):
        filtered = [i for i in filtered if str(i.get('code') or '').upper() == str(merged.get('code')).upper()]
    if not _p2_is_all(merged.get('code_prefix')):
        prefix = str(merged.get('code_prefix')).upper()
        filtered = [i for i in filtered if str(i.get('code') or '').upper().startswith(prefix)]
    if not _p2_is_all(merged.get('category')):
        wanted = str(merged.get('category')).lower()
        filtered = [i for i in filtered if _p2_event_category(i).lower() == wanted or (wanted == 'warnings' and _p2_event_severity(i) in {'warning','error'})]
    if not _p2_is_all(merged.get('severity')):
        wanted = str(merged.get('severity')).lower()
        filtered = [i for i in filtered if _p2_event_severity(i) == wanted]
    if not _p2_is_all(merged.get('correlation')):
        wanted = str(merged.get('correlation')).lower()
        filtered = [i for i in filtered if wanted in _p2_corr(i).lower() or wanted in _p2_blob(i)]
    query = merged.get('q') if not _p2_is_all(merged.get('q')) else merged.get('contains')
    if not _p2_is_all(query):
        needle = str(query).lower()
        filtered = [i for i in filtered if needle in _p2_blob(i)]
    order = str(merged.get('order') or 'desc').lower()
    filtered.sort(key=lambda i: _p2_float(i.get('ts')), reverse=order != 'asc')
    limit = merged.get('limit')
    if limit is not None and limit != '':
        filtered = filtered[:max(0, _p2_int(limit))]
    return filtered


def build_audit_summary_text(payload: _P2Any = None, logs: _P2Any = None) -> str:
    data = _p2_dict(payload)
    raw = logs if logs is not None else data.get('events') or data.get('items') or data.get('logs') or []
    events = [dict(i) for i in _p2_list(raw) if isinstance(i, dict)]
    summary = _p2_dict(data.get('summary') or data.get('event_summary'))
    categories = dict(_p2_dict(summary.get('categories') or summary.get('category_counts') or data.get('categories') or data.get('category_counts')))
    severities = dict(_p2_dict(summary.get('severities') or summary.get('severity_counts') or data.get('severities') or data.get('severity_counts')))
    codes = dict(_p2_dict(summary.get('codes') or summary.get('code_counts') or data.get('codes') or data.get('code_counts')))
    for item in events:
        cat = _p2_event_category(item); sev = _p2_event_severity(item); code = str(item.get('code') or '-')
        categories[cat] = categories.get(cat, 0) + 1
        severities[sev] = severities.get(sev, 0) + 1
        codes[code] = codes.get(code, 0) + 1
    total = _p2_int(data.get('total', data.get('total_events', len(events))), len(events))
    fmt = lambda d: ', '.join(f'{k}:{v}' for k, v in sorted(d.items())) if d else '-'
    warn = _p2_int(severities.get('warning', severities.get('WARN', 0)))
    err = _p2_int(severities.get('error', severities.get('ERROR', 0)))
    return '\n'.join(['Audit Viewer','------------',f'Contract        : {AUDIT_VIEWER_CONTRACT_VERSION}',f'Total events    : {total}',f'Rendered count  : {len(events)}',f'Filtered events : {len(events)}',f'Warnings/errors : {warn} / {err}',f'Categories      : {fmt(categories)}',f'Severities      : {fmt(severities)}',f'Codes           : {fmt(codes)}',f'Top codes       : {fmt(codes)}'])


def _p2_get_filter(app: _P2Any, *names: str, default: _P2Any = None) -> _P2Any:
    for name in names:
        obj = _p2_getattr(app, name, None)
        if obj is not None:
            val = _p2_var_value(obj, obj)
            if val is not None:
                return val
    return default


def _p2_collect_events(app: _P2Any) -> list[dict[str, _P2Any]]:
    for name in ('_audit_events','_last_audit_events','audit_events','_last_logs','logs','_logs'):
        val = _p2_getattr(app, name, None)
        if isinstance(val, list):
            return [dict(i) for i in val if isinstance(i, dict)]
    api_get = _p2_getattr(app, 'api_get', None)
    if callable(api_get):
        try:
            payload = api_get('/events/audit', timeout=2.0)
            if isinstance(payload, dict):
                return [dict(i) for i in _p2_list(payload.get('events') or payload.get('items') or payload.get('logs')) if isinstance(i, dict)]
            if isinstance(payload, list):
                return [dict(i) for i in payload if isinstance(i, dict)]
        except Exception:
            return []
    return []


def _p2_render_logs(self: _P2Any, payload: _P2Any = None) -> None:
    events = [dict(i) for i in _p2_list(_p2_dict(payload).get('events') if isinstance(payload, dict) else None) if isinstance(i, dict)] or _p2_collect_events(self)
    filters = {
        'category': _p2_get_filter(self, 'audit_category_var','audit_category_filter','category_filter', default='All'),
        'severity': _p2_get_filter(self, 'audit_severity_var','audit_severity_filter','severity_filter', default='All'),
        'code_prefix': _p2_get_filter(self, 'audit_code_prefix_var','audit_code_prefix_filter', default=None),
        'q': _p2_get_filter(self, 'audit_search_var','audit_query_var','audit_text_var','search_var', default=None),
        'correlation': _p2_get_filter(self, 'audit_correlation_var','audit_correlation_filter', default=None),
    }
    filtered = filter_audit_events(events, filters)
    _p2_set_text(self, 'audit-box', '\n'.join(format_log_line(i) for i in filtered))
    _p2_set_text(self, 'audit-summary-box', build_audit_summary_text({'total': len(events)}, filtered))


def _p2_render_session_summary(self: _P2Any, status: dict[str, _P2Any] | None = None) -> None:
    status = _p2_dict(status or _p2_getattr(self, '_last_status', {}))
    logs = [dict(i) for i in _p2_list(_p2_getattr(self, '_last_logs', None) or _p2_getattr(self, '_log_items', None)) if isinstance(i, dict)]
    reset_ts = None
    for item in logs:
        if str(item.get('code') or '').upper() == 'RISK_STATS_RESET':
            reset_ts = _p2_float(item.get('ts'))
    closed = []
    for item in logs:
        if str(item.get('code') or '').upper() == 'POSITION_CLOSED' and (reset_ts is None or _p2_float(item.get('ts')) > reset_ts):
            data = _p2_dict(item.get('data'))
            closed.append(_p2_float(data.get('pnl', item.get('pnl'))))
    wins = sum(1 for p in closed if p > 0)
    losses = sum(1 for p in closed if p < 0)
    be = sum(1 for p in closed if p == 0)
    pnl = sum(closed)
    daily = _p2_int(_p2_dict(status.get('session')).get('daily_trade_count', len(closed)), len(closed))
    lines = [f"Current signal  : {status.get('last_signal','-')}", f"Signal reason   : {status.get('signal_reason','-')}", f"Trend           : {status.get('trend','-')}", f"Tracked PnL     : {pnl:.6f}", f"Trades today    : {daily}", f"Today W/L/BE    : {wins}/{losses}/{be}", f"Today trades    : {' / '.join(str(p) for p in closed) or '-'}", f"Scope note      : {'-' if daily == len(closed) else f'partial log scope ({len(closed)}/{daily})'}"]
    _p2_set_text(self, 'log-box', '\n'.join(lines))


def _p2_render_event_timeline(self: _P2Any, status: dict[str, _P2Any] | None = None) -> None:
    events = _p2_collect_events(self)
    category = _p2_get_filter(self, 'event_category_var','event_filter','event_category_filter', default='All')
    filtered = filter_audit_events(events, {'category': category, 'order': 'asc'})
    _p2_set_text(self, 'event-box', '\n'.join(format_log_line(i) for i in filtered))
    _p2_cfg(_p2_getattr(self, 'event_count_label', None), text=f'{category}: {len(filtered)} event' if not _p2_is_all(category) else f'All: {len(filtered)} event')


def _p2_render_status(self: _P2Any, status: dict[str, _P2Any]) -> None:
    status = _p2_dict(status)
    health = _p2_dict(status.get('health_snapshot'))
    ok = lambda v: 'OK' if str(v or 'HEALTHY').upper() in {'HEALTHY','OK'} else str(v)
    position = _p2_position(status)
    _p2_set_text(self, 'status-box', '\n'.join([f"Account         : {ok(health.get('account_consistency'))}", f"Position health : {ok(health.get('position_consistency'))}", f"Pending health  : {ok(health.get('pending_consistency'))}", build_position_management_text({'position_snapshot': position})]))
    _p2_set_text(self, 'position-box', build_position_management_text({'position_snapshot': position}))
    _p2_set_text(self, 'risk-box', 'Safe mode       : ' + str(_p2_bool(_p2_dict(status.get('risk_snapshot')).get('safe_mode'))))
    _p2_set_text(self, 'ai-box', 'Model           : ' + str(_p2_dict(status.get('ai_snapshot')).get('model_path', '-')))
    _p2_set_text(self, 'pending-box', 'Pending order   : ' + ('YES' if _p2_pending_present(status) else 'NO'))
    _p2_apply_health_aware_controls(self, status)


def _p2_apply_health_aware_controls(self: _P2Any, status: dict[str, _P2Any] | None = None) -> None:
    controls = build_operator_control_state(status or _p2_getattr(self, '_last_status', {}) or {}, connected=_p2_bool(_p2_getattr(self, '_last_connected', True)))
    try: setattr(self, '_last_operator_control_state', controls)
    except Exception: pass
    mapping = {'btn_force_buy':'force_buy', 'btn_force_sell':'force_sell', 'btn_cancel_pending':'cancel_pending', 'btn_safe_mode_toggle':'safe_mode', 'btn_balance_sync':'balance_sync', 'btn_ai_reload':'ai_reload', 'btn_start':'start', 'btn_stop':'stop'}
    for attr, key in mapping.items():
        enabled = _p2_bool(_p2_dict(controls.get('buttons')).get(key))
        _p2_cfg(_p2_getattr(self, attr, None), state='normal' if enabled else 'disabled', fg_color=('#3B8ED0','#1F6AA5') if enabled else ('#8C8C8C','#5F5F5F'))
    for attr in ('operator_hint','operator_hint_label','lbl_operator_hint','lbl_control_hint','control_hint','controls_hint'):
        _p2_cfg(_p2_getattr(self, attr, None), text=controls.get('hint'))
        _p2_direct_set(_p2_getattr(self, attr, None), str(controls.get('hint')))


def _p2_action_from_path(path: str) -> str | None:
    raw = str(path).lower().replace('_','-')
    if 'force-buy' in raw: return 'force_buy'
    if 'force-sell' in raw: return 'force_sell'
    if 'cancel' in raw: return 'cancel_pending'
    return None


def _p2_api_post(self: _P2Any, path: str, payload: dict[str, _P2Any] | None = None, **kwargs: _P2Any) -> bool:
    action = kwargs.get('action') or _p2_action_from_path(path)
    controls = _p2_dict(_p2_getattr(self, '_last_operator_control_state', {})) or build_operator_control_state(_p2_getattr(self, '_last_status', {}) or {}, connected=_p2_bool(_p2_getattr(self, '_last_connected', True)))
    if action and not _p2_bool(_p2_dict(controls.get('buttons')).get(action, controls.get(action))):
        return False
    delegate = _p2_getattr(self, 'api_post', None)
    if callable(delegate):
        try:
            delegate(path, payload or {}, **kwargs)
        except Exception:
            return False
    return True


def _p2_set_offline_ui(self: _P2Any, reason: str = '-') -> None:
    text = f'Backend çevrimdışı ({reason})\nBackend offline.\nReason: {reason}'
    for target in ('status-box','log-box','ai-box','risk-box','position-box','pending-box'):
        _p2_set_text(self, target, text)
    _p2_cfg(_p2_getattr(self, 'lbl_connection', None), text='Backend: OFFLINE', text_color=('red','orange'))


def _p2_poll_health_and_status(self: _P2Any) -> None:
    try:
        health = self.api_get('/health', timeout=1.0)
    except Exception as exc:
        _p2_set_offline_ui(self, str(exc))
        return
    _p2_cfg(_p2_getattr(self, 'lbl_connection', None), text='Backend: ONLINE', text_color=('green','light green'))
    try:
        status = self.api_get('/status', timeout=2.0)
    except Exception:
        _p2_set_text(self, 'status-box', 'Backend online, status payload alınamadı')
        return
    _p2_render_status(self, status)


def _p2_extract_training_output_path(self: _P2Any, line: str) -> str | None:
    raw = str(line or '').strip()
    if not raw: return None
    for parser in (_p2_json.loads, _p2_ast.literal_eval):
        try:
            obj = parser(raw)
            if isinstance(obj, dict):
                for key in ('model_path','output','output_path','model','path'):
                    if obj.get(key): return str(obj.get(key))
        except Exception:
            pass
    for marker in ('model_path=', 'output=', 'output_path='):
        if marker in raw:
            return raw.split(marker, 1)[1].strip().strip('"\'').split()[0].strip(',;')
    return None


def _p2_patch_dashboard_classes() -> None:
    for _name, _obj in list(globals().items()):
        if isinstance(_obj, type) and ('Dashboard' in _name or _name.endswith('App')):
            _obj._render_logs = _p2_render_logs
            _obj._render_session_summary = _p2_render_session_summary
            _obj._render_event_timeline = _p2_render_event_timeline
            _obj._render_status = _p2_render_status
            _obj._apply_health_aware_controls = _p2_apply_health_aware_controls
            _obj._api_post = _p2_api_post
            _obj._set_offline_ui = _p2_set_offline_ui
            _obj._poll_health_and_status = _p2_poll_health_and_status
            _obj._extract_training_output_path = _p2_extract_training_output_path

_p2_patch_dashboard_classes()
# END 4B.4.3.6.6.20P2 DASHBOARD CONTRACT FIX
'''


def strip_old_blocks(text: str) -> tuple[str, bool]:
    pattern = re.compile(r"\n?# BEGIN 4B\.4\.3\.6\.6\.20[A-Z0-9]*[^\n]*.*?# END 4B\.4\.3\.6\.6\.20[A-Z0-9]*[^\n]*(?:\n|$)", re.DOTALL)
    new, count = pattern.subn('\n', text)
    return new.rstrip() + '\n', count > 0


def main() -> int:
    root = Path.cwd()
    dash = root / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
    if not dash.exists():
        raise RuntimeError(f'dashboard.py not found: {dash}')
    text = dash.read_text(encoding='utf-8')
    text, removed = strip_old_blocks(text)
    text = text.rstrip() + '\n\n' + COMPAT_BLOCK.strip() + '\n'
    dash.write_text(text, encoding='utf-8')
    checks = {
        'old_blocks_removed': removed,
        'force_buy_casing': 'Force BUY ready' in text,
        'safe_mode_key': "'safe_mode': safe_mode" in text,
        'pending_hint': 'PENDING_ORDER_ACTIVE' in text,
        'take_profit_text': 'Take profit' in text,
        'code_prefix_upper': "params['code_prefix'] = str(code_prefix).upper()" in text,
        'status_box_set_text': "'status-box'" in text,
        'log_box_set_text': "'log-box'" in text,
        'class_auto_patch': '_p2_patch_dashboard_classes()' in text,
    }
    print('4B.4.3.6.6.20p2 dashboard contract fix applied')
    for k, v in checks.items():
        print(f' - {k}: {v}')
    if not all(checks.values()):
        raise RuntimeError(f'20p2 checks failed: {checks}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
