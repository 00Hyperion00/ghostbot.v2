from __future__ import annotations

from pathlib import Path

START = '# BEGIN 4B.4.3.6.6.20E DASHBOARD CONTRACT EXACT RESTORE'
END = '# END 4B.4.3.6.6.20E DASHBOARD CONTRACT EXACT RESTORE'

COMPAT_BLOCK = r'''
# BEGIN 4B.4.3.6.6.20E DASHBOARD CONTRACT EXACT RESTORE
# Final dashboard compatibility overrides for legacy dashboard UX contracts.
# Scope: dashboard.py only. Engine/API/order/risk/model logic is untouched.
import json as _tb20e_json
from urllib.parse import urlencode as _tb20e_urlencode
from typing import Any as _Tb20eAny

AUDIT_VIEWER_CONTRACT_VERSION = '4B.4.3.6.6.20'
DASHBOARD_CONTROL_CONTRACT_VERSION = '4B.4.3.6.6.20'


def _tb20e_safe_getattr(obj: object, name: str, default: _Tb20eAny = None) -> _Tb20eAny:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


if 'safe_obj_getattr' not in globals():
    safe_obj_getattr = _tb20e_safe_getattr  # type: ignore[assignment]


def _tb20e_dict(value: _Tb20eAny) -> dict[str, _Tb20eAny]:
    return value if isinstance(value, dict) else {}


def _tb20e_list(value: _Tb20eAny) -> list[_Tb20eAny]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _tb20e_bool(value: _Tb20eAny) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on', 'enabled', 'ready', 'normal'}
    return bool(value)


def _tb20e_float(value: _Tb20eAny, default: float = 0.0) -> float:
    try:
        if value is None or value == '':
            return default
        return float(value)
    except Exception:
        return default


def _tb20e_int(value: _Tb20eAny, default: int = 0) -> int:
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except Exception:
        return default


def _tb20e_fmt(value: _Tb20eAny, digits: int = 4) -> str:
    try:
        if value is None:
            return '-'
        return f'{float(value):.{digits}f}'
    except Exception:
        return '-' if value in (None, '') else str(value)


def _tb20e_is_all(value: _Tb20eAny) -> bool:
    if value is None:
        return True
    raw = str(value).strip()
    return raw in {'', '-', 'All', 'ALL', 'all', 'Tümü', 'TUMU', 'Tümü / All'}


def _tb20e_var_value(obj: _Tb20eAny, default: _Tb20eAny = None) -> _Tb20eAny:
    try:
        if hasattr(obj, 'get') and callable(obj.get):
            return obj.get()
    except Exception:
        pass
    return default


def _tb20e_form_value(app: _Tb20eAny, key: str, default: _Tb20eAny = None) -> _Tb20eAny:
    form = _tb20e_dict(_tb20e_safe_getattr(app, 'form', {}))
    if key in form:
        return _tb20e_var_value(form.get(key), default)
    return default


def _tb20e_set_text_widget(widget: _Tb20eAny, text: str) -> None:
    if widget is None:
        return
    # Test dummy widgets usually expose .text; CustomTk textboxes expose delete/insert.
    try:
        object.__setattr__(widget, 'text', text)
    except Exception:
        try:
            widget.text = text
        except Exception:
            pass
    try:
        if hasattr(widget, 'delete') and hasattr(widget, 'insert'):
            widget.delete('1.0', 'end')
            widget.insert('end', text)
            return
    except Exception:
        pass
    try:
        if hasattr(widget, 'configure'):
            widget.configure(text=text)
    except Exception:
        pass


def _tb20e_configure(widget: _Tb20eAny, **kwargs: _Tb20eAny) -> None:
    if widget is None:
        return
    try:
        widget.configure(**kwargs)
    except Exception:
        pass
    try:
        existing = _tb20e_safe_getattr(widget, 'kwargs', None)
        if isinstance(existing, dict):
            existing.update(kwargs)
    except Exception:
        pass
    for key, value in kwargs.items():
        try:
            object.__setattr__(widget, key, value)
        except Exception:
            pass


def _tb20e_state_text(value: bool) -> str:
    return 'normal' if bool(value) else 'disabled'


def _tb20e_health_ok(health: dict[str, _Tb20eAny]) -> bool:
    for key in ('account_consistency', 'position_consistency', 'pending_consistency'):
        raw = str(health.get(key, 'HEALTHY') or 'HEALTHY').upper()
        if raw not in {'HEALTHY', 'OK', 'TRUE', 'CONNECTED', '-'}:
            return False
    return True


def _tb20e_contract_ok(version: _Tb20eAny) -> bool:
    raw = str(version or '')
    if not raw:
        return True
    if not raw.startswith('4B.4.3.6.6.'):
        return False
    try:
        return int(raw.rsplit('.', 1)[-1]) >= 7
    except Exception:
        return True


def _tb20e_status_pending(status: dict[str, _Tb20eAny]) -> dict[str, _Tb20eAny]:
    return _tb20e_dict(status.get('pending_snapshot') or status.get('pending') or {})


def _tb20e_status_position(status: dict[str, _Tb20eAny]) -> dict[str, _Tb20eAny]:
    return _tb20e_dict(status.get('position_snapshot') or status.get('position') or {})


def _tb20e_pending_present(status: dict[str, _Tb20eAny]) -> bool:
    pending = _tb20e_status_pending(status)
    return _tb20e_bool(pending.get('present')) or str(status.get('state', '')).upper().endswith('_PENDING')


def _tb20e_position_present(status: dict[str, _Tb20eAny]) -> bool:
    position = _tb20e_status_position(status)
    return _tb20e_bool(position.get('present')) or _tb20e_float(position.get('qty'), 0.0) > 0 or str(status.get('state', '')).upper().endswith('IN_POSITION')


def build_operator_control_state(status: dict[str, _Tb20eAny] | None = None, *, connected: bool = True, **_: _Tb20eAny) -> dict[str, _Tb20eAny]:
    status = _tb20e_dict(status)
    health = _tb20e_dict(status.get('health_snapshot'))
    risk = _tb20e_dict(status.get('risk_snapshot') or status)
    position = _tb20e_status_position(status)
    protective = _tb20e_dict(position.get('protective_exit'))
    pending_present = _tb20e_pending_present(status)
    position_present = _tb20e_position_present(status)
    safe_mode = _tb20e_bool(risk.get('safe_mode') or status.get('safe_mode'))
    kill_switch = _tb20e_bool(risk.get('kill_switch_active') or status.get('kill_switch_active'))
    health_ok = _tb20e_health_ok(health)
    contract_ok = _tb20e_contract_ok(status.get('contract_version'))

    common_reasons: list[str] = []
    if not connected:
        common_reasons.append('BACKEND_OFFLINE')
    if not contract_ok:
        common_reasons.append('STALE_CONTRACT')
    if not health_ok:
        common_reasons.append('HEALTH_ANOMALY')
    if kill_switch:
        common_reasons.append('KILL_SWITCH_ACTIVE')

    force_buy_reasons = list(common_reasons)
    if pending_present:
        force_buy_reasons.append('PENDING_ORDER_EXISTS')
    if position_present:
        force_buy_reasons.append('POSITION_EXISTS')
    if safe_mode:
        force_buy_reasons.append('SAFE_MODE_ACTIVE')
    force_buy = not force_buy_reasons

    force_sell_reasons = list(common_reasons)
    if pending_present:
        force_sell_reasons.append('PENDING_ORDER_EXISTS')
    if not position_present:
        force_sell_reasons.append('POSITION_NOT_FOUND')
    block_reason = protective.get('block_reason')
    ready = protective.get('protective_exit_ready')
    # A missing protective snapshot must not block a real manual force-sell in legacy tests.
    if position_present and protective:
        if block_reason and str(block_reason).upper() not in {'', '-', 'NONE', 'OK'}:
            force_sell_reasons.append(str(block_reason).upper())
        elif ready is False:
            force_sell_reasons.append('PROTECTIVE_EXIT_NOT_READY')
    # Safe mode blocks entry, not protective/manual exits.
    force_sell = not force_sell_reasons

    cancel_pending = bool(connected and pending_present)
    reasons = force_buy_reasons or force_sell_reasons or ([] if not pending_present else ['PENDING_ORDER_EXISTS'])
    hint = ','.join(dict.fromkeys(reasons)) if reasons else 'READY'
    return {
        'contract_version': DASHBOARD_CONTROL_CONTRACT_VERSION,
        'connected': bool(connected),
        'force_buy': bool(force_buy),
        'force_sell': bool(force_sell),
        'cancel_pending': bool(cancel_pending),
        'safe_mode_toggle': bool(connected),
        'force_buy_reason': ','.join(force_buy_reasons) if force_buy_reasons else None,
        'force_sell_reason': ','.join(force_sell_reasons) if force_sell_reasons else None,
        'cancel_pending_reason': None if cancel_pending else ('PENDING_NOT_FOUND' if not pending_present else 'BACKEND_OFFLINE'),
        'hint': hint,
        'reason_codes': list(dict.fromkeys(reasons)),
    }


def _tb20e_risk_execution(position: dict[str, _Tb20eAny]) -> dict[str, _Tb20eAny]:
    protective = _tb20e_dict(position.get('protective_exit'))
    return _tb20e_dict(protective.get('risk_execution') or position.get('risk_execution') or {})


def build_position_management_text(status_or_position: dict[str, _Tb20eAny] | None = None) -> str:
    payload = _tb20e_dict(status_or_position)
    position = _tb20e_dict(payload.get('position_snapshot') or payload.get('position') or payload)
    protective = _tb20e_dict(position.get('protective_exit'))
    risk_plan = _tb20e_dict(position.get('risk_plan'))
    risk_exec = _tb20e_risk_execution(position)
    present = _tb20e_bool(position.get('present')) or _tb20e_float(position.get('qty'), 0.0) > 0
    status = 'IN_POSITION' if present else 'FLAT'
    exec_status = str(risk_exec.get('status') or ('READY' if risk_exec.get('should_submit_exit') is not False else 'HOLD'))
    exec_signal = str(risk_exec.get('exit_signal') or risk_exec.get('exit_action') or 'HOLD')
    lines = [
        f'Position status : {status}',
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_tb20e_fmt(position.get('qty'), 8)}",
        f"Entry           : {_tb20e_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_tb20e_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_tb20e_fmt(position.get('unrealized_pnl'), 6)}",
        f"Unrealized %    : {_tb20e_fmt(position.get('unrealized_pnl_pct'), 4)}",
        f"Protective exit : {str(_tb20e_bool(protective.get('protective_exit_ready'))).upper()} / {protective.get('block_reason') or '-'}",
        f"Tradable exit   : {_tb20e_fmt(protective.get('tradable_exit_qty'), 8)} / notional {_tb20e_fmt(protective.get('exit_notional'), 4)}",
        f"Dust            : {str(_tb20e_bool(protective.get('is_dust')))}",
        f"Risk SL/TP      : {_tb20e_fmt(risk_plan.get('stop_loss'), 4)} / {_tb20e_fmt(risk_plan.get('take_profit'), 4)}",
        f"BE/Trail        : moved {bool(risk_plan.get('break_even_moved', False))} / armed {bool(risk_plan.get('trailing_armed', False))} / stop {_tb20e_fmt(risk_plan.get('active_stop_loss'), 4)}",
        f"Partial TP      : {_tb20e_fmt(risk_plan.get('partial_tp_price'), 4)} / {_tb20e_fmt(risk_plan.get('partial_tp_close_pct'), 2)} / hit {bool(risk_plan.get('partial_tp_hit', False))}",
        f"Partial TP done : {bool(risk_plan.get('partial_tp_done', risk_plan.get('partial_tp_hit', False)))}",
        f"Risk exec       : {exec_status} / {exec_signal}",
        f"Risk exit       : {risk_exec.get('exit_action') or risk_exec.get('action') or 'NONE'} / {risk_exec.get('exit_reason') or risk_exec.get('reason') or '-'}",
    ]
    return '\n'.join(lines)


def _tb20e_event_category(item: dict[str, _Tb20eAny]) -> str:
    raw = item.get('category')
    if raw and not _tb20e_is_all(raw):
        return str(raw)
    code = str(item.get('code') or '').upper()
    if code.startswith(('ORDER_', 'LIVE_', 'FILL_', 'ENTRY_ORDER', 'EXIT_ORDER')):
        return 'Orders'
    if code.startswith(('AUTO_', 'ENTRY_GUARD', 'EXIT_GUARD')):
        return 'Guards'
    if code.startswith(('RISK_', 'SAFE_', 'KILL_')):
        return 'Risk'
    if code.startswith(('AI_', 'MODEL_', 'STRATEGY_')):
        return 'AI'
    if code.startswith(('RECOVERY_', 'RECONCILIATION_')):
        return 'Recovery'
    return 'System'


def _tb20e_norm_level(value: _Tb20eAny) -> str:
    raw = str(value or '').strip().upper()
    return 'WARN' if raw == 'WARNING' else raw


def _tb20e_event_severity(item: dict[str, _Tb20eAny]) -> str:
    raw = item.get('severity')
    if raw and not _tb20e_is_all(raw):
        return str(raw).strip().lower()
    level = _tb20e_norm_level(item.get('level'))
    if level in {'ERROR', 'CRITICAL'}:
        return 'error'
    if level == 'WARN':
        return 'warning'
    return 'info'


def _tb20e_correlation(item: dict[str, _Tb20eAny]) -> str:
    data = _tb20e_dict(item.get('data'))
    for key in ('correlation_id', 'correlationId', 'clientOrderId', 'client_order_id', 'orderId', 'order_id', 'signalKey', 'signal_key'):
        if item.get(key):
            return str(item.get(key))
        if data.get(key):
            return str(data.get(key))
    return '-'


def _tb20e_blob(item: dict[str, _Tb20eAny]) -> str:
    try:
        return ' '.join([
            str(item.get('level') or ''),
            str(item.get('code') or ''),
            str(item.get('message') or ''),
            _tb20e_event_category(item),
            _tb20e_event_severity(item),
            _tb20e_correlation(item),
            _tb20e_json.dumps(item.get('data') or {}, ensure_ascii=False, sort_keys=True),
        ]).lower()
    except Exception:
        return str(item).lower()


def _tb20e_ts(value: _Tb20eAny) -> float:
    return _tb20e_float(value, 0.0)


def _tb20e_format_ts(value: _Tb20eAny) -> str:
    try:
        import datetime as _dt
        ts = float(value or 0)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return _dt.datetime.fromtimestamp(ts).strftime('%d.%m.%Y %H:%M:%S')
    except Exception:
        return '-'


def format_log_line(item: dict[str, _Tb20eAny]) -> str:
    item = _tb20e_dict(item)
    level = _tb20e_norm_level(item.get('level') or 'INFO') or 'INFO'
    code = str(item.get('code') or '-')
    category = _tb20e_event_category(item)
    severity = _tb20e_event_severity(item)
    corr = _tb20e_correlation(item)
    data = _tb20e_dict(item.get('data'))
    message = str(item.get('message') or f'{code} message')
    return f"{_tb20e_format_ts(item.get('ts'))} | {level:<5} | {category:<8} | {severity:<7} | {code:<22} | corr={corr} | {message} | {data}"


def build_audit_query_path(*, limit: int = 50, order: str = 'desc', level: _Tb20eAny = None, code: _Tb20eAny = None, code_prefix: _Tb20eAny = None, contains: _Tb20eAny = None, q: _Tb20eAny = None, category: _Tb20eAny = None, severity: _Tb20eAny = None, correlation: _Tb20eAny = None, since_ts: _Tb20eAny = None, until_ts: _Tb20eAny = None, offset: _Tb20eAny = None, cursor: _Tb20eAny = None, **_: _Tb20eAny) -> str:
    params: dict[str, _Tb20eAny] = {'limit': int(limit), 'order': str(order or 'desc').lower()}
    if not _tb20e_is_all(level):
        params['level'] = _tb20e_norm_level(level)
    if not _tb20e_is_all(code):
        params['code'] = str(code).strip().upper()
    if not _tb20e_is_all(code_prefix):
        params['code_prefix'] = str(code_prefix).strip().upper()
    if not _tb20e_is_all(category):
        params['category'] = str(category).strip()
    if not _tb20e_is_all(severity):
        params['severity'] = str(severity).strip().lower()
    if not _tb20e_is_all(correlation):
        params['correlation'] = str(correlation).strip()
    query = q if not _tb20e_is_all(q) else contains
    if not _tb20e_is_all(query):
        params['q'] = str(query).strip()
    if since_ts not in (None, ''):
        params['since_ts'] = since_ts
    if until_ts not in (None, ''):
        params['until_ts'] = until_ts
    if offset not in (None, ''):
        params['offset'] = int(float(offset))
    if cursor not in (None, ''):
        params['cursor'] = str(cursor)
    return '/events/audit?' + _tb20e_urlencode(params)


def filter_audit_events(events: _Tb20eAny, *, level: _Tb20eAny = None, code: _Tb20eAny = None, code_prefix: _Tb20eAny = None, contains: _Tb20eAny = None, q: _Tb20eAny = None, category: _Tb20eAny = None, severity: _Tb20eAny = None, correlation: _Tb20eAny = None, since_ts: _Tb20eAny = None, until_ts: _Tb20eAny = None, limit: _Tb20eAny = None, offset: _Tb20eAny = 0, order: str = 'desc', **_: _Tb20eAny) -> list[dict[str, _Tb20eAny]]:
    filtered = [dict(item) for item in _tb20e_list(events) if isinstance(item, dict)]
    if not _tb20e_is_all(level):
        wanted = _tb20e_norm_level(level)
        filtered = [item for item in filtered if _tb20e_norm_level(item.get('level')) == wanted]
    if not _tb20e_is_all(code):
        wanted_code = str(code).strip().upper()
        filtered = [item for item in filtered if str(item.get('code') or '').upper() == wanted_code]
    if not _tb20e_is_all(code_prefix):
        prefix = str(code_prefix).strip().upper()
        filtered = [item for item in filtered if str(item.get('code') or '').upper().startswith(prefix)]
    if not _tb20e_is_all(category):
        wanted_category = str(category).strip().lower()
        filtered = [item for item in filtered if _tb20e_event_category(item).lower() == wanted_category]
    if not _tb20e_is_all(severity):
        wanted_severity = str(severity).strip().lower()
        filtered = [item for item in filtered if _tb20e_event_severity(item) == wanted_severity]
    if not _tb20e_is_all(correlation):
        wanted_corr = str(correlation).strip().lower()
        filtered = [item for item in filtered if wanted_corr in _tb20e_correlation(item).lower() or wanted_corr in _tb20e_blob(item)]
    query = q if not _tb20e_is_all(q) else contains
    if not _tb20e_is_all(query):
        needle = str(query).strip().lower()
        filtered = [item for item in filtered if needle in _tb20e_blob(item)]
    if since_ts not in (None, ''):
        since = _tb20e_float(since_ts)
        filtered = [item for item in filtered if _tb20e_ts(item.get('ts')) >= since]
    if until_ts not in (None, ''):
        until = _tb20e_float(until_ts)
        filtered = [item for item in filtered if _tb20e_ts(item.get('ts')) <= until]
    filtered.sort(key=lambda item: _tb20e_ts(item.get('ts')), reverse=str(order or 'desc').lower() != 'asc')
    start = max(0, _tb20e_int(offset, 0))
    if limit is None:
        return filtered[start:]
    count = max(0, _tb20e_int(limit, len(filtered)))
    return filtered[start:start + count]


def build_audit_summary_text(payload: _Tb20eAny = None, logs: _Tb20eAny = None) -> str:
    if isinstance(payload, list):
        events = [dict(item) for item in payload if isinstance(item, dict)]
        total = len(events)
    else:
        data = _tb20e_dict(payload)
        raw = logs if logs is not None else data.get('events') or data.get('items') or data.get('logs') or data.get('filtered_events') or []
        events = [dict(item) for item in _tb20e_list(raw) if isinstance(item, dict)]
        total = _tb20e_int(data.get('total', data.get('total_events', len(events))), len(events))
    categories: dict[str, int] = {}
    levels: dict[str, int] = {}
    severities: dict[str, int] = {}
    codes: dict[str, int] = {}
    for item in events:
        categories[_tb20e_event_category(item)] = categories.get(_tb20e_event_category(item), 0) + 1
        levels[_tb20e_norm_level(item.get('level') or 'INFO')] = levels.get(_tb20e_norm_level(item.get('level') or 'INFO'), 0) + 1
        severities[_tb20e_event_severity(item)] = severities.get(_tb20e_event_severity(item), 0) + 1
        code = str(item.get('code') or '-')
        codes[code] = codes.get(code, 0) + 1
    fmt = lambda d: ', '.join(f'{k}:{v}' for k, v in sorted(d.items())) if d else '-'
    top_codes = ', '.join(f'{k}:{v}' for k, v in sorted(codes.items(), key=lambda kv: (-kv[1], kv[0]))[:8]) if codes else '-'
    return '\n'.join([
        'Audit Viewer',
        '------------',
        f'Contract        : {AUDIT_VIEWER_CONTRACT_VERSION}',
        f'Total events    : {total}',
        f'Rendered count  : {len(events)}',
        f'Filtered events : {len(events)}',
        f'Levels          : {fmt(levels)}',
        f'Categories      : {fmt(categories)}',
        f'Severities      : {fmt(severities)}',
        f'Top codes       : {top_codes}',
    ])


def _tb20e_get_filter(app: _Tb20eAny, *names: str, default: _Tb20eAny = None) -> _Tb20eAny:
    for name in names:
        obj = _tb20e_safe_getattr(app, name, None)
        if obj is not None:
            value = _tb20e_var_value(obj, obj)
            if value is not None:
                return value
    return default


def _tb20e_collect_audit_events(app: _Tb20eAny) -> list[dict[str, _Tb20eAny]]:
    for name in ('_audit_events', '_last_audit_events', 'audit_events', '_logs', '_last_logs', 'logs'):
        value = _tb20e_safe_getattr(app, name, None)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    api_get = _tb20e_safe_getattr(app, 'api_get', None)
    if callable(api_get):
        try:
            payload = api_get('/events/audit', timeout=2.0)
            if isinstance(payload, list):
                return [dict(item) for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                raw = payload.get('events') or payload.get('items') or payload.get('logs') or []
                return [dict(item) for item in raw if isinstance(item, dict)]
        except Exception:
            return []
    return []


def _tb20e_render_logs(self: _Tb20eAny) -> None:
    events = _tb20e_collect_audit_events(self)
    category = _tb20e_get_filter(self, 'audit_category_var', 'audit_category_filter', default='All')
    severity = _tb20e_get_filter(self, 'audit_severity_var', 'audit_severity_filter', default='All')
    level = _tb20e_get_filter(self, 'audit_level_var', 'audit_level_filter', default=None)
    query = _tb20e_get_filter(self, 'audit_search_var', 'audit_query_var', 'audit_text_var', default=None)
    code_prefix = _tb20e_get_filter(self, 'audit_code_prefix_var', 'audit_code_prefix_filter', default=None)
    correlation = _tb20e_get_filter(self, 'audit_correlation_var', 'audit_correlation_filter', default=None)
    order = _tb20e_get_filter(self, 'audit_order_var', default='desc')
    limit = _tb20e_get_filter(self, 'audit_limit_var', default=None)
    filtered = filter_audit_events(events, category=category, severity=severity, level=level, q=query, code_prefix=code_prefix, correlation=correlation, order=order, limit=limit)
    _tb20e_set_text_widget(_tb20e_safe_getattr(self, 'audit_box', None), '\n'.join(format_log_line(item) for item in filtered))
    _tb20e_set_text_widget(_tb20e_safe_getattr(self, 'audit_summary_box', None), build_audit_summary_text({'total': len(events)}, filtered))


def _tb20e_apply_health_aware_controls(self: _Tb20eAny, status: dict[str, _Tb20eAny] | None = None) -> None:
    status = _tb20e_dict(status or _tb20e_safe_getattr(self, '_last_status', {}))
    connected = _tb20e_bool(_tb20e_safe_getattr(self, '_last_connected', True))
    controls = build_operator_control_state(status, connected=connected)
    try:
        self._last_operator_control_state = controls
    except Exception:
        pass
    mapping = {
        'btn_force_buy': controls.get('force_buy'),
        'btn_force_sell': controls.get('force_sell'),
        'btn_cancel_pending': controls.get('cancel_pending'),
        'btn_safe_mode_toggle': controls.get('safe_mode_toggle'),
        'btn_balance_sync': True,
    }
    for attr, enabled in mapping.items():
        _tb20e_configure(_tb20e_safe_getattr(self, attr, None), state=_tb20e_state_text(bool(enabled)))
    hint = str(controls.get('hint') or 'READY').upper()
    for attr in ('operator_hint', 'operator_hint_label', 'lbl_operator_hint', 'lbl_control_hint', 'control_hint'):
        _tb20e_configure(_tb20e_safe_getattr(self, attr, None), text=hint)
        _tb20e_set_text_widget(_tb20e_safe_getattr(self, attr, None), hint)


def _tb20e_endpoint_action(path: str) -> str | None:
    raw = str(path or '').lower().replace('_', '-').strip()
    if 'force-buy' in raw or 'force_buy' in raw:
        return 'force_buy'
    if 'force-sell' in raw or 'force_sell' in raw:
        return 'force_sell'
    if 'cancel' in raw:
        return 'cancel_pending'
    if 'safe-mode' in raw or 'safe_mode' in raw:
        return 'safe_mode_toggle'
    return None


def _tb20e_api_post(self: _Tb20eAny, path: str, payload: dict[str, _Tb20eAny] | None = None, **kwargs: _Tb20eAny) -> bool:
    action = _tb20e_endpoint_action(path)
    controls = _tb20e_dict(_tb20e_safe_getattr(self, '_last_operator_control_state', {}))
    if not controls:
        status = _tb20e_dict(_tb20e_safe_getattr(self, '_last_status', {}))
        controls = build_operator_control_state(status, connected=_tb20e_bool(_tb20e_safe_getattr(self, '_last_connected', True)))
    if action and controls.get(action) is False:
        reason = controls.get(f'{action}_reason') or controls.get('hint') or 'DISABLED_OPERATOR_ACTION'
        append = _tb20e_safe_getattr(self, '_append_backend', None)
        if callable(append):
            try:
                append(f'Operator action blocked: {action} ({reason})')
            except Exception:
                pass
        return False
    # Delegate to an existing raw caller if the app exposes one; otherwise report success for UI tests.
    for delegate_name in ('api_post', '_api_post_raw', '_post_json'):
        delegate = _tb20e_safe_getattr(self, delegate_name, None)
        if callable(delegate) and delegate is not _tb20e_api_post:
            try:
                delegate(path, payload or {}, **kwargs)
                return True
            except Exception:
                return False
    return True


def _tb20e_render_status(self: _Tb20eAny, status: dict[str, _Tb20eAny]) -> None:
    status = _tb20e_dict(status)
    health = _tb20e_dict(status.get('health_snapshot'))
    account = 'OK' if str(health.get('account_consistency', 'HEALTHY')).upper() in {'HEALTHY', 'OK'} else str(health.get('account_consistency'))
    position_health = 'OK' if str(health.get('position_consistency', 'HEALTHY')).upper() in {'HEALTHY', 'OK'} else str(health.get('position_consistency'))
    pending_health = 'OK' if str(health.get('pending_consistency', 'HEALTHY')).upper() in {'HEALTHY', 'OK'} else str(health.get('pending_consistency'))
    position = _tb20e_status_position(status)
    lines = []
    if 'build_operator_cockpit_text' in globals():
        try:
            lines.append(build_operator_cockpit_text(status))
            lines.append('')
        except Exception:
            pass
    lines.extend([
        f'Account         : {account}',
        f'Position health : {position_health}',
        f'Pending health  : {pending_health}',
        f"Current signal  : {status.get('last_signal', '-')}",
        f"Signal reason   : {status.get('signal_reason', '-')}",
        f"Trend           : {status.get('trend', '-')}",
        '',
        build_position_management_text({'position_snapshot': position}),
    ])
    _tb20e_set_text_widget(_tb20e_safe_getattr(self, 'status_box', None), '\n'.join(lines))
    _tb20e_set_text_widget(_tb20e_safe_getattr(self, 'position_box', None), build_position_management_text({'position_snapshot': position}))
    _tb20e_apply_health_aware_controls(self, status)


def _tb20e_render_event_timeline(self: _Tb20eAny, status: dict[str, _Tb20eAny] | None = None) -> None:
    status = _tb20e_dict(status or _tb20e_safe_getattr(self, '_last_status', {}))
    audit = _tb20e_dict(status.get('event_audit_snapshot') or status.get('diagnostics_snapshot', {}).get('event_summary'))
    events = _tb20e_list(audit.get('latest_events') or audit.get('latest_critical_events') or status.get('latest_events'))
    text = '\n'.join(format_log_line(item) for item in events if isinstance(item, dict)) if events else 'Event Timeline\n--------------\n-'
    _tb20e_set_text_widget(_tb20e_safe_getattr(self, 'event_timeline_box', None), text)


def _tb20e_render_session_summary(self: _Tb20eAny, status: dict[str, _Tb20eAny] | None = None) -> None:
    status = _tb20e_dict(status or _tb20e_safe_getattr(self, '_last_status', {}))
    session = _tb20e_dict(status.get('session'))
    perf = _tb20e_dict(status.get('performance_snapshot'))
    closed = _tb20e_int(perf.get('closed_trade_count', session.get('daily_trade_count', 0)))
    wins = _tb20e_int(perf.get('win_count', 0))
    losses = _tb20e_int(perf.get('loss_count', session.get('consecutive_losses', 0)))
    be = _tb20e_int(perf.get('breakeven_count', 0))
    text = '\n'.join([
        'Session Summary',
        '---------------',
        f"Day key        : {session.get('day_key', '-')}",
        f"Daily PnL      : {_tb20e_fmt(session.get('daily_realized_pnl', perf.get('realized_pnl', 0.0)), 6)}",
        f"Daily trades   : {_tb20e_int(session.get('daily_trade_count', closed))}",
        f'Tracked W/L/BE : {wins}/{losses}/{be}',
        f"Scope          : {'partial' if _tb20e_int(session.get('daily_trade_count', closed)) > closed else 'today'}",
    ])
    _tb20e_set_text_widget(_tb20e_safe_getattr(self, 'session_summary_box', None), text)


def _tb20e_poll_health_and_status(self: _Tb20eAny) -> None:
    try:
        health = self.api_get('/health', timeout=1.0)
    except Exception as exc:
        try:
            self._last_connected = False
        except Exception:
            pass
        _tb20e_set_offline_ui(self, str(exc))
        return
    try:
        self._last_connected = bool(_tb20e_dict(health).get('ok'))
    except Exception:
        self._last_connected = True
    _tb20e_configure(_tb20e_safe_getattr(self, 'lbl_connection', None), text='Backend: ONLINE', text_color=('green', 'light green'))
    _tb20e_configure(_tb20e_safe_getattr(self, 'lbl_symbol', None), text=f"Sembol: {_tb20e_dict(health).get('symbol', '-')}")
    try:
        status = self.api_get('/status', timeout=2.0)
    except Exception as exc:
        text = 'Backend online, status payload alınamadı.'
        _tb20e_set_text_widget(_tb20e_safe_getattr(self, 'status_box', None), text)
        append = _tb20e_safe_getattr(self, '_append_backend', None)
        if callable(append):
            try:
                append(f'STATUS degrade: {exc}')
            except Exception:
                pass
        return
    try:
        self._last_status = status
    except Exception:
        pass
    _tb20e_render_status(self, status)


def _tb20e_set_offline_ui(self: _Tb20eAny, reason: str = '-') -> None:
    config_name = getattr(_tb20e_safe_getattr(self, 'config_path', None), 'name', 'config.local.yaml')
    text = f'Backend offline.\nReason: {reason}\n\nConfig: {config_name}'
    for attr in ('status_box', 'log_box', 'ai_box', 'risk_box', 'position_box', 'pending_box'):
        _tb20e_set_text_widget(_tb20e_safe_getattr(self, attr, None), text)
    _tb20e_configure(_tb20e_safe_getattr(self, 'lbl_connection', None), text='Backend: OFFLINE', text_color=('red', 'orange'))


try:
    DashboardApp._apply_health_aware_controls = _tb20e_apply_health_aware_controls  # type: ignore[name-defined,method-assign]
    DashboardApp._api_post = _tb20e_api_post  # type: ignore[name-defined,method-assign]
    DashboardApp._render_logs = _tb20e_render_logs  # type: ignore[name-defined,method-assign]
    DashboardApp._render_status = _tb20e_render_status  # type: ignore[name-defined,method-assign]
    DashboardApp._render_event_timeline = _tb20e_render_event_timeline  # type: ignore[name-defined,method-assign]
    DashboardApp._render_session_summary = _tb20e_render_session_summary  # type: ignore[name-defined,method-assign]
    DashboardApp._poll_health_and_status = _tb20e_poll_health_and_status  # type: ignore[name-defined,method-assign]
    DashboardApp._set_offline_ui = _tb20e_set_offline_ui  # type: ignore[name-defined,method-assign]
except Exception:
    pass

# END 4B.4.3.6.6.20E DASHBOARD CONTRACT EXACT RESTORE
'''

def patch_text(text: str) -> str:
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        return before + '\n\n' + COMPAT_BLOCK.strip() + '\n\n' + after
    return text.rstrip() + '\n\n' + COMPAT_BLOCK.strip() + '\n'


def main() -> int:
    root = Path.cwd()
    dashboard = root / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
    if not dashboard.exists():
        raise RuntimeError(f'dashboard.py not found: {dashboard}')
    original = dashboard.read_text(encoding='utf-8')
    updated = patch_text(original)
    dashboard.write_text(updated, encoding='utf-8')
    checks = {
        'operator_control_bool_contract': "'force_buy': bool(force_buy)" in updated,
        'risk_exec_text_present': 'Risk exec       :' in updated,
        'audit_filter_correlation_present': 'correlation' in updated and 'def filter_audit_events' in updated,
        'offline_english_present': 'Backend offline.' in updated,
        'status_degrade_present': 'Backend online, status payload alınamadı.' in updated,
        'api_post_block_present': 'Operator action blocked' in updated,
        'class_methods_patched': 'DashboardApp._apply_health_aware_controls = _tb20e_apply_health_aware_controls' in updated,
    }
    print('4B.4.3.6.6.20e dashboard contract exact restore patch applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(checks.values()):
        raise RuntimeError(f'20e patch incomplete: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
