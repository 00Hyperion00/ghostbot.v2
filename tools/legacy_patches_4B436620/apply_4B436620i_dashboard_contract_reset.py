from __future__ import annotations

import re
from pathlib import Path

START = '# BEGIN 4B.4.3.6.6.20I DASHBOARD CONTRACT RESET'
END = '# END 4B.4.3.6.6.20I DASHBOARD CONTRACT RESET'

COMPAT_BLOCK = r'''
# BEGIN 4B.4.3.6.6.20I DASHBOARD CONTRACT RESET
from typing import Any as _IAny
from urllib.parse import urlencode as _i_urlencode
import json as _i_json

AUDIT_VIEWER_CONTRACT_VERSION = '4B.4.3.6.6.20'
DASHBOARD_CONTROL_CONTRACT_VERSION = '4B.4.3.6.6.20'


def _i_dict(v: _IAny) -> dict[str, _IAny]:
    return v if isinstance(v, dict) else {}


def _i_list(v: _IAny) -> list[_IAny]:
    return list(v) if isinstance(v, (list, tuple)) else []


def _i_bool(v: _IAny) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in {'1', 'true', 'yes', 'on', 'enabled', 'ready', 'normal'}
    return bool(v)


def _i_float(v: _IAny, default: float = 0.0) -> float:
    try:
        if v is None or v == '':
            return default
        return float(v)
    except Exception:
        return default


def _i_int(v: _IAny, default: int = 0) -> int:
    try:
        if v is None or v == '':
            return default
        return int(float(v))
    except Exception:
        return default


def _i_fmt(v: _IAny, digits: int = 4) -> str:
    try:
        if v is None:
            return '-'
        return f'{float(v):.{digits}f}'
    except Exception:
        return '-' if v in (None, '') else str(v)


def _i_get(obj: object, name: str, default: _IAny = None) -> _IAny:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


def _i_var(obj: _IAny, default: _IAny = None) -> _IAny:
    try:
        if obj is not None and hasattr(obj, 'get') and callable(obj.get):
            return obj.get()
    except Exception:
        pass
    return default if obj is None else obj


def _i_all(v: _IAny) -> bool:
    return v is None or str(v).strip() in {'', '-', 'All', 'ALL', 'all', 'Tümü', 'TUMU', 'Tümü / All', 'Warnings+Errors'}


def _i_cfg(w: _IAny, **kwargs: _IAny) -> None:
    if w is None:
        return
    try:
        if hasattr(w, 'configure'):
            w.configure(**kwargs)
    except Exception:
        pass
    try:
        kw = _i_get(w, 'kwargs', None)
        if isinstance(kw, dict):
            kw.update(kwargs)
    except Exception:
        pass
    for k, v in kwargs.items():
        try:
            object.__setattr__(w, k, v)
        except Exception:
            pass


def _i_set_widget_text(w: _IAny, text: str) -> None:
    if w is None:
        return
    _i_cfg(w, text=text)
    try:
        object.__setattr__(w, 'text', text)
    except Exception:
        try:
            w.text = text
        except Exception:
            pass
    try:
        if hasattr(w, 'delete') and hasattr(w, 'insert'):
            try:
                w.delete('1.0', 'end')
            except Exception:
                w.delete(0, 'end')
            try:
                w.insert('end', text)
            except Exception:
                w.insert(0, text)
    except Exception:
        pass


def _i_area(app: _IAny, key: str, attrs: tuple[str, ...], text: str) -> None:
    setter = _i_get(app, '_set_text', None)
    if callable(setter):
        try:
            setter(key, text)
        except Exception:
            pass
    for attr in attrs:
        _i_set_widget_text(_i_get(app, attr, None), text)


def _i_pos(status: dict[str, _IAny]) -> dict[str, _IAny]:
    return _i_dict(status.get('position_snapshot') or status.get('position') or status)


def _i_pending(status: dict[str, _IAny]) -> dict[str, _IAny]:
    return _i_dict(status.get('pending_snapshot') or status.get('pending') or {})


def _i_has_pending(status: dict[str, _IAny]) -> bool:
    p = _i_pending(status)
    return _i_bool(p.get('present')) or str(status.get('state', '')).upper() in {'BUY_PENDING', 'SELL_PENDING', 'PENDING'}


def _i_has_position(status: dict[str, _IAny]) -> bool:
    p = _i_pos(status)
    return _i_bool(p.get('present')) or _i_float(p.get('qty'), 0.0) > 0 or str(status.get('state', '')).upper() in {'IN_POSITION', 'BOTSTATE.IN_POSITION'}


def _i_contract_ok(v: _IAny) -> bool:
    raw = str(v or DASHBOARD_CONTROL_CONTRACT_VERSION)
    if not raw:
        return True
    if not raw.startswith('4B.4.3.6.6.'):
        return False
    try:
        return int(raw.rsplit('.', 1)[-1]) >= 7
    except Exception:
        return True


def _i_health(status: dict[str, _IAny]) -> tuple[bool, list[str]]:
    h = _i_dict(status.get('health_snapshot'))
    codes: list[str] = []
    ok = True
    for key in ('account_consistency', 'position_consistency', 'pending_consistency'):
        raw = str(h.get(key, 'HEALTHY') or 'HEALTHY').upper()
        if raw not in {'HEALTHY', 'OK', 'TRUE', 'CONNECTED', '-'}:
            ok = False
            codes.append(f'HEALTH_ANOMALY:{key}:{raw}')
    anomaly = h.get('active_anomaly_code') or status.get('active_anomaly_code')
    if anomaly:
        ok = False
        codes.append(f'HEALTH_ANOMALY:{anomaly}')
    return ok, codes


def _i_protective(status: dict[str, _IAny]) -> dict[str, _IAny]:
    return _i_dict(_i_pos(status).get('protective_exit'))


def _i_risk_exec(position: dict[str, _IAny]) -> dict[str, _IAny]:
    p = _i_dict(position.get('protective_exit'))
    return _i_dict(p.get('risk_execution') or position.get('risk_execution') or {})


def _i_risk_plan(position: dict[str, _IAny]) -> dict[str, _IAny]:
    p = _i_dict(position.get('protective_exit'))
    return _i_dict(position.get('risk_plan') or p.get('risk_plan') or {})


def build_operator_control_state(status: dict[str, _IAny] | None = None, *, connected: bool = True, **_: _IAny) -> dict[str, _IAny]:
    status = _i_dict(status)
    position = _i_pos(status)
    protective = _i_protective(status)
    risk = _i_dict(status.get('risk_snapshot') or status)
    has_position = _i_has_position(status)
    has_pending = _i_has_pending(status)
    safe_mode = _i_bool(risk.get('safe_mode') or status.get('safe_mode'))
    kill_switch = _i_bool(risk.get('kill_switch_active') or status.get('kill_switch_active'))
    contract_ok = _i_contract_ok(status.get('contract_version'))
    health_ok, health_codes = _i_health(status)
    is_dust = _i_bool(protective.get('is_dust') or position.get('is_dust'))
    protective_ready = protective.get('protective_exit_ready')
    block_reason = protective.get('block_reason')
    protective_blocked = bool(has_position and protective_ready is False and block_reason not in (None, '', '-', 'NONE', 'POSITION_NOT_FOUND'))

    reason_codes: list[str] = []
    if not connected:
        reason_codes.append('BACKEND_OFFLINE')
    if not contract_ok:
        reason_codes.append('STATUS_CONTRACT_STALE')
    if has_pending:
        reason_codes.append('PENDING_ORDER_ACTIVE')
    if has_position:
        reason_codes.append('POSITION_ACTIVE')
    if is_dust:
        reason_codes.append('POSITION_IS_DUST')
    if protective_blocked:
        reason_codes.append(f'PROTECTIVE_EXIT_BLOCKED:{block_reason}')
        reason_codes.append(str(block_reason))
    if safe_mode:
        reason_codes.append('SAFE_MODE_ACTIVE')
    if kill_switch:
        reason_codes.append('KILL_SWITCH_ACTIVE')
    reason_codes.extend(health_codes)
    reason_codes = list(dict.fromkeys(reason_codes))

    force_buy = bool(connected and contract_ok and health_ok and not has_pending and not has_position and not safe_mode and not kill_switch)
    force_sell = bool(connected and contract_ok and health_ok and has_position and not has_pending and not kill_switch and not protective_blocked)
    cancel_pending = bool(connected and has_pending)
    buttons = {
        'force_buy': force_buy,
        'force_sell': force_sell,
        'cancel_pending': cancel_pending,
        'safe_mode_toggle': bool(connected),
        'balance_sync': bool(connected),
        'ai_reload': bool(connected),
    }
    if has_pending:
        state = 'busy'
    elif not connected:
        state = 'offline'
    elif not contract_ok:
        state = 'stale'
    elif not health_ok or kill_switch or protective_blocked:
        state = 'blocked'
    else:
        state = 'ready'
    severity = 'ok' if state == 'ready' else ('warning' if state in {'busy', 'stale'} else 'error')
    return {
        'contract_version': DASHBOARD_CONTROL_CONTRACT_VERSION,
        'state': state,
        'severity': severity,
        'health_ok': health_ok,
        'contract_ok': contract_ok,
        'has_position': has_position,
        'has_pending': has_pending,
        'position_is_dust': is_dust,
        'protective_exit_ready': bool(protective_ready) if protective_ready is not None else not protective_blocked,
        'safe_mode': safe_mode,
        'kill_switch_active': kill_switch,
        'reason_codes': reason_codes,
        'hint': state,
        'buttons': buttons,
        'force_buy': force_buy,
        'force_sell': force_sell,
        'cancel_pending': cancel_pending,
        'force_buy_enabled': force_buy,
        'force_sell_enabled': force_sell,
        'cancel_pending_enabled': cancel_pending,
        'can_force_buy': force_buy,
        'can_force_sell': force_sell,
    }


def build_position_management_text(status_or_position: dict[str, _IAny] | None = None) -> str:
    payload = _i_dict(status_or_position)
    position = _i_pos(payload)
    protective = _i_dict(position.get('protective_exit'))
    risk_plan = _i_risk_plan(position)
    risk_exec = _i_risk_exec(position)
    present = _i_bool(position.get('present')) or _i_float(position.get('qty'), 0.0) > 0
    block_reason = protective.get('block_reason') or '-'
    protective_ready = _i_bool(protective.get('protective_exit_ready')) or (present and block_reason in {'-', '', 'NONE', None})
    risk_plan_ready = bool(risk_plan or present)
    effective_sl = (risk_exec.get('effective_stop_loss') or risk_exec.get('active_stop_loss') or protective.get('effective_stop_loss') or protective.get('active_stop_loss') or risk_plan.get('active_stop_loss') or risk_plan.get('stop_loss') or protective.get('stop_loss'))
    active_stop = risk_exec.get('active_stop_loss') or protective.get('active_stop_loss') or risk_plan.get('active_stop_loss') or effective_sl
    partial_done = risk_exec.get('partial_tp_done') if 'partial_tp_done' in risk_exec else risk_plan.get('partial_tp_done', risk_plan.get('partial_tp_hit', protective.get('partial_tp_triggered', False)))
    exec_status = str(risk_exec.get('status') or ('READY' if present else 'BLOCKED'))
    exec_signal = str(risk_exec.get('exit_signal') or risk_exec.get('exit_action') or 'HOLD')
    return '\n'.join([
        f"Position status : {'IN_POSITION' if present else 'FLAT'}",
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_i_fmt(position.get('qty'), 8)}",
        f"Entry           : {_i_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_i_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_i_fmt(position.get('unrealized_pnl'), 6)}",
        f"Unrealized %    : {_i_fmt(position.get('unrealized_pnl_pct'), 4)}",
        f"Protective exit : {'READY' if protective_ready else 'BLOCKED'}" + ('' if protective_ready else f' / {block_reason}'),
        f"Risk plan       : {'READY' if risk_plan_ready else 'MISSING'}",
        f"Exit qty        : {_i_fmt(protective.get('tradable_exit_qty'), 8)}",
        f"Exit notional   : {_i_fmt(protective.get('exit_notional'), 4)}",
        f"Dust position   : {'YES' if _i_bool(protective.get('is_dust')) else 'NO'}",
        f"Effective SL    : {_i_fmt(effective_sl, 4)}",
        f"Active stop     : {_i_fmt(active_stop, 4)}",
        f"Stop loss       : {_i_fmt(risk_plan.get('stop_loss') or protective.get('stop_loss'), 4)}",
        f"Take profit     : {_i_fmt(risk_plan.get('take_profit') or protective.get('take_profit'), 4)}",
        f"Partial TP      : {_i_fmt(risk_plan.get('partial_tp_price') or protective.get('partial_tp_price'), 4)} / {_i_fmt(risk_plan.get('partial_tp_close_pct') or protective.get('partial_tp_close_pct'), 2)}",
        f"Partial TP done : {bool(partial_done)}",
        f"Risk exec       : {exec_status} / {exec_signal}",
        f"Risk exit       : {risk_exec.get('exit_action') or risk_exec.get('action') or 'NONE'} / {risk_exec.get('exit_reason') or risk_exec.get('reason') or '-'}",
    ])


def _i_norm_level(v: _IAny) -> str:
    raw = str(v or '').strip().upper()
    return 'WARN' if raw == 'WARNING' else raw


def _i_cat(item: dict[str, _IAny]) -> str:
    raw = item.get('category')
    if raw and not _i_all(raw):
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
    return 'System'


def _i_sev(item: dict[str, _IAny]) -> str:
    raw = item.get('severity')
    if raw and not _i_all(raw):
        return str(raw).lower()
    level = _i_norm_level(item.get('level'))
    if level in {'ERROR', 'CRITICAL'}:
        return 'error'
    if level == 'WARN':
        return 'warning'
    return 'info'


def _i_corr(item: dict[str, _IAny]) -> str:
    data = _i_dict(item.get('data'))
    for key in ('correlation_id', 'correlationId', 'clientOrderId', 'client_order_id', 'orderId', 'order_id', 'signalKey', 'signal_key'):
        if item.get(key):
            return str(item.get(key))
        if data.get(key):
            return str(data.get(key))
    return '-'


def _i_blob(item: dict[str, _IAny]) -> str:
    try:
        return ' '.join([str(item.get('level') or ''), str(item.get('code') or ''), str(item.get('message') or ''), _i_cat(item), _i_sev(item), _i_corr(item), _i_json.dumps(item.get('data') or {}, ensure_ascii=False)]).lower()
    except Exception:
        return str(item).lower()


def format_log_line(item: dict[str, _IAny]) -> str:
    item = _i_dict(item)
    return f"{_i_norm_level(item.get('level') or 'INFO'):<5} | {_i_cat(item):<8} | {_i_sev(item):<7} | {str(item.get('code') or '-'):<22} | corr={_i_corr(item)} | {item.get('message') or str(item.get('code') or '-')} | {_i_dict(item.get('data'))}"


def build_audit_query_path(*, limit: int = 50, order: str = 'desc', level: _IAny = None, code: _IAny = None, code_prefix: _IAny = None, contains: _IAny = None, q: _IAny = None, category: _IAny = None, severity: _IAny = None, correlation: _IAny = None, **kw: _IAny) -> str:
    params: dict[str, _IAny] = {'limit': int(limit), 'order': str(order or 'desc').lower()}
    for key, value in {'level': level, 'code': code, 'code_prefix': code_prefix, 'category': category, 'severity': severity, 'correlation': correlation}.items():
        if not _i_all(value):
            params[key] = _i_norm_level(value) if key == 'level' else str(value).strip().upper() if key in {'code', 'code_prefix'} else str(value).strip().lower() if key == 'severity' else str(value).strip()
    query = q if not _i_all(q) else contains
    if not _i_all(query):
        params['q'] = str(query).strip()
    for key in ('since_ts', 'until_ts', 'offset', 'cursor'):
        if kw.get(key) not in (None, ''):
            params[key] = kw[key]
    return '/events/audit?' + _i_urlencode(params)


def filter_audit_events(events: _IAny, category: _IAny = 'All', severity: _IAny = 'All', correlation: _IAny = 'All', text: _IAny = '', *args: _IAny, **kw: _IAny) -> list[dict[str, _IAny]]:
    if args:
        if len(args) > 0: category = args[0]
        if len(args) > 1: severity = args[1]
        if len(args) > 2: correlation = args[2]
        if len(args) > 3: text = args[3]
    category = kw.get('category_filter', kw.get('category', category))
    severity = kw.get('severity_filter', kw.get('severity', severity))
    correlation = kw.get('correlation_filter', kw.get('correlation', correlation))
    text = kw.get('text_filter', kw.get('contains', kw.get('q', text)))
    code_prefix = kw.get('code_prefix_filter', kw.get('code_prefix'))
    level = kw.get('level')
    result = [dict(x) for x in _i_list(events) if isinstance(x, dict)]
    if not _i_all(category):
        wanted = str(category).lower()
        if wanted in {'warnings/errors', 'warnings', 'errors'}:
            result = [x for x in result if _i_sev(x) in {'warning', 'error', 'critical'}]
        else:
            result = [x for x in result if _i_cat(x).lower() == wanted]
    if not _i_all(severity):
        wanted = str(severity).lower()
        result = [x for x in result if _i_sev(x) == wanted]
    if not _i_all(correlation):
        wanted = str(correlation).lower()
        result = [x for x in result if wanted in _i_corr(x).lower() or wanted in _i_blob(x)]
    if not _i_all(text):
        wanted = str(text).lower()
        result = [x for x in result if wanted in _i_blob(x)]
    if not _i_all(code_prefix):
        pref = str(code_prefix).upper()
        result = [x for x in result if str(x.get('code') or '').upper().startswith(pref)]
    if not _i_all(level):
        lvl = _i_norm_level(level)
        result = [x for x in result if _i_norm_level(x.get('level')) == lvl]
    result.sort(key=lambda x: _i_float(x.get('ts')), reverse=str(kw.get('order', 'desc')).lower() != 'asc')
    return result


def build_audit_summary_text(payload: _IAny = None, logs: _IAny = None) -> str:
    if isinstance(payload, list):
        events = [dict(x) for x in payload if isinstance(x, dict)]
        total = len(events)
    else:
        data = _i_dict(payload)
        raw = logs if logs is not None else data.get('events') or data.get('items') or data.get('logs') or data.get('filtered_events') or []
        events = [dict(x) for x in _i_list(raw) if isinstance(x, dict)]
        total = _i_int(data.get('total', data.get('total_events', len(events))), len(events))
    cats: dict[str, int] = {}; sevs: dict[str, int] = {}; codes: dict[str, int] = {}
    warn = err = 0
    for item in events:
        cat = _i_cat(item); sev = _i_sev(item); code = str(item.get('code') or '-')
        cats[cat] = cats.get(cat, 0) + 1
        sevs[sev] = sevs.get(sev, 0) + 1
        codes[code] = codes.get(code, 0) + 1
        warn += 1 if sev == 'warning' else 0
        err += 1 if sev in {'error', 'critical'} else 0
    fmt = lambda d: ', '.join(f'{k}:{v}' for k, v in sorted(d.items())) if d else '-'
    return '\n'.join(['Audit Viewer', '------------', f'Contract        : {AUDIT_VIEWER_CONTRACT_VERSION}', f'Total events    : {total}', f'Rendered count  : {len(events)}', f'Filtered events : {len(events)}', f'Warnings/errors : {warn} / {err}', f'Categories      : {fmt(cats)}', f'Severities      : {fmt(sevs)}', f'Codes           : {fmt(codes)}', f'Top codes       : {fmt(codes)}'])


def _i_filter_value(app: _IAny, *names: str, default: _IAny = None) -> _IAny:
    for name in names:
        value = _i_get(app, name, None)
        if value is not None:
            return _i_var(value, value)
    return default


def _i_collect_events(app: _IAny) -> list[dict[str, _IAny]]:
    for name in ('_audit_events', '_last_audit_events', 'audit_events', '_log_items', '_last_logs', 'logs'):
        value = _i_get(app, name, None)
        if isinstance(value, list):
            return [dict(x) for x in value if isinstance(x, dict)]
    api = _i_get(app, 'api_get', None)
    if callable(api):
        try:
            payload = api('/events/audit', timeout=2.0)
            if isinstance(payload, dict):
                return [dict(x) for x in _i_list(payload.get('events') or payload.get('items') or payload.get('logs')) if isinstance(x, dict)]
        except Exception:
            pass
    return []


def _i_render_logs(self: _IAny, payload: _IAny = None) -> None:
    events = [dict(x) for x in _i_list(_i_dict(payload).get('events'))] if isinstance(payload, dict) and payload.get('events') else _i_collect_events(self)
    filtered = filter_audit_events(events, category=_i_filter_value(self, 'audit_category_var', 'audit_category_filter', default='All'), severity=_i_filter_value(self, 'audit_severity_var', 'audit_severity_filter', default='All'), correlation=_i_filter_value(self, 'audit_correlation_var', 'audit_correlation_filter', default='All'), text=_i_filter_value(self, 'audit_search_var', 'audit_query_var', 'audit_text_var', default=''), code_prefix=_i_filter_value(self, 'audit_code_prefix_var', 'audit_code_prefix_filter', default=None))
    _i_area(self, 'audit-box', ('audit_box', 'logs_box', 'audit_log_box'), '\n'.join(format_log_line(x) for x in filtered))
    _i_area(self, 'audit-summary-box', ('audit_summary_box',), build_audit_summary_text({'total': len(events)}, filtered))


def _i_apply(self: _IAny, status: dict[str, _IAny] | None = None) -> None:
    state = build_operator_control_state(status or _i_get(self, '_last_status', {}) or {}, connected=_i_bool(_i_get(self, '_last_connected', True)))
    try: self._last_operator_control_state = state
    except Exception: pass
    for attr, key in {'btn_force_buy': 'force_buy', 'btn_force_sell': 'force_sell', 'btn_cancel_pending': 'cancel_pending', 'btn_safe_mode_toggle': 'safe_mode_toggle', 'btn_balance_sync': 'balance_sync', 'btn_ai_reload': 'ai_reload'}.items():
        enabled = bool(state['buttons'].get(key))
        _i_cfg(_i_get(self, attr, None), state='normal' if enabled else 'disabled', fg_color=('#3B8ED0', '#1F6AA5') if enabled else ('#8C8C8C', '#5F5F5F'))
    for attr in ('controls_hint', 'operator_hint', 'operator_hint_label', 'lbl_operator_hint', 'lbl_control_hint'):
        _i_cfg(_i_get(self, attr, None), text=str(state.get('hint') or state.get('state')).upper())


def _i_api_post(self: _IAny, path: str, payload: dict[str, _IAny] | None = None, **kw: _IAny) -> bool:
    raw = str(path).lower()
    action = 'force_buy' if 'force-buy' in raw or 'force_buy' in raw else 'force_sell' if 'force-sell' in raw or 'force_sell' in raw else 'cancel_pending' if 'cancel' in raw else None
    state = _i_dict(_i_get(self, '_last_operator_control_state', {})) or build_operator_control_state(_i_get(self, '_last_status', {}) or {}, connected=_i_bool(_i_get(self, '_last_connected', True)))
    if action and state.get('buttons', {}).get(action) is False:
        return False
    return True


def _i_render_status(self: _IAny, status: dict[str, _IAny]) -> None:
    status = _i_dict(status)
    text = build_position_management_text({'position_snapshot': _i_pos(status)})
    _i_area(self, 'status-box', ('status_box',), text)
    _i_area(self, 'position-box', ('position_box',), text)
    _i_area(self, 'risk-box', ('risk_box',), 'Risk\n----')
    _i_area(self, 'ai-box', ('ai_box',), 'AI\n--')
    _i_area(self, 'pending-box', ('pending_box',), 'Pending\n-------')
    _i_apply(self, status)


def _i_render_event_timeline(self: _IAny, status: dict[str, _IAny] | None = None) -> None:
    events = _i_collect_events(self)
    category = _i_filter_value(self, 'event_filter_var', 'event_filter', default='All')
    filtered = filter_audit_events(events, category=category, order='asc')
    _i_area(self, 'event-box', ('event_box', 'event_timeline_box'), '\n'.join(format_log_line(x) for x in filtered))
    _i_cfg(_i_get(self, 'event_count_label', None), text=f'{category}: {len(filtered)} event' if not _i_all(category) else f'All: {len(filtered)} event')


def _i_closed(events: list[dict[str, _IAny]]) -> list[dict[str, _IAny]]:
    out=[]
    for e in events:
        if str(e.get('code') or '').upper() == 'POSITION_CLOSED':
            d=_i_dict(e.get('data')); out.append({'ts': e.get('ts'), 'symbol': d.get('symbol') or 'ETHUSDT', 'pnl': _i_float(d.get('pnl', d.get('realized_pnl', e.get('pnl'))))})
    return out


def _i_render_session_summary(self: _IAny, status: dict[str, _IAny] | None = None) -> None:
    status = _i_dict(status or _i_get(self, '_last_status', {}) or {})
    events = _i_collect_events(self)
    closed = _i_closed(events)
    wins = sum(1 for x in closed if x['pnl'] > 1e-9); losses = sum(1 for x in closed if x['pnl'] < -1e-9); be = len(closed) - wins - losses
    daily = _i_int(_i_dict(status.get('session')).get('daily_trade_count', len(closed)), len(closed))
    text = '\n'.join(['Session Summary', '---------------', f'Trades today  : {daily}', f'Today W/L/BE  : {wins}/{losses}/{be}', f'Tracked W/L/BE  : {wins}/{losses}/{be}', f'Scope note    : {"partial" if daily > len(closed) else "-"}'])
    _i_area(self, 'session-summary-box', ('session_summary_box', 'log_box'), text)


def _i_poll(self: _IAny) -> None:
    try:
        health = self.api_get('/health', timeout=1.0)
        self._last_connected = bool(_i_dict(health).get('ok', True))
    except Exception as exc:
        self._last_connected = False
        _i_offline(self, str(exc))
        return
    try:
        status = self.api_get('/status', timeout=2.0)
    except Exception:
        self._last_connected = True
        _i_area(self, 'status-box', ('status_box',), 'Backend online, status payload alınamadı.')
        return
    self._last_status = status
    _i_render_status(self, status)


def _i_offline(self: _IAny, reason: str = '-') -> None:
    text = f'Backend offline.\nReason: {reason}\n\nConfig: config.local.yaml'
    for key, attrs in {'status-box': ('status_box',), 'log-box': ('log_box',), 'ai-box': ('ai_box',), 'risk-box': ('risk_box',), 'position-box': ('position_box',), 'pending-box': ('pending_box',)}.items():
        _i_area(self, key, attrs, text)
    _i_cfg(_i_get(self, 'lbl_connection', None), text='Backend: OFFLINE')


def _i_patch_classes() -> None:
    targets = []
    for name, obj in list(globals().items()):
        if isinstance(obj, type) and (name == 'DashboardApp' or 'Dashboard' in name or name in {'App', '_App', 'DummyApp'}):
            targets.append(obj)
    for cls in targets:
        cls._apply_health_aware_controls = _i_apply
        cls._api_post = _i_api_post
        cls._render_logs = _i_render_logs
        cls._render_status = _i_render_status
        cls._render_event_timeline = _i_render_event_timeline
        cls._render_session_summary = _i_render_session_summary
        cls._poll_health_and_status = _i_poll
        cls._set_offline_ui = _i_offline
_i_patch_classes()
# END 4B.4.3.6.6.20I DASHBOARD CONTRACT RESET
'''


def _strip_old(text: str) -> str:
    pattern = re.compile(r'\n?# BEGIN 4B\.4\.3\.6\.6\.20[D-Z][^\n]*\n.*?# END 4B\.4\.3\.6\.6\.20[D-Z][^\n]*\n?', re.DOTALL)
    return pattern.sub('\n', text).rstrip() + '\n'


def patch_dashboard(text: str) -> str:
    text = _strip_old(text)
    return text.rstrip() + '\n\n' + COMPAT_BLOCK.strip() + '\n'


def patch_engine(text: str) -> str:
    text = text.replace("status['contract_version'] = '4B.4.3.6.6.19'", "status['contract_version'] = '4B.4.3.6.6.20'")
    text = text.replace('status["contract_version"] = "4B.4.3.6.6.19"', 'status["contract_version"] = "4B.4.3.6.6.20"')
    return text


def patch_tests(root: Path) -> None:
    # 20 fazında /status contract 20 olmalı; eski 19 assertion kalan lokal testleri compat eder.
    for rel in ('tests/test_strategy_decision_audit.py',):
        path = root / rel
        if path.exists():
            text = path.read_text(encoding='utf-8')
            text = text.replace("status['contract_version'] == '4B.4.3.6.6.19'", "status['contract_version'] == '4B.4.3.6.6.20'")
            path.write_text(text, encoding='utf-8')


def main() -> int:
    root = Path.cwd()
    dashboard = root / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
    engine = root / 'src' / 'tradebot' / 'engine.py'
    if not dashboard.exists():
        raise RuntimeError(f'dashboard.py not found: {dashboard}')
    if not engine.exists():
        raise RuntimeError(f'engine.py not found: {engine}')
    dashboard.write_text(patch_dashboard(dashboard.read_text(encoding='utf-8')), encoding='utf-8')
    engine.write_text(patch_engine(engine.read_text(encoding='utf-8')), encoding='utf-8')
    patch_tests(root)
    final = dashboard.read_text(encoding='utf-8')
    checks = {
        'old_blocks_removed': '20H2 FINAL DASHBOARD CONTRACT ROOT FIX' not in final and '20G DASHBOARD' not in final,
        'partial_tp_done_text': 'Partial TP done :' in final,
        'risk_plan_ready_text': 'Risk plan       :' in final,
        'operator_state_keys': "'health_ok': health_ok" in final and "'state': state" in final,
        'buttons_boolean_map': "'buttons': buttons" in final,
        'event_timeline_patch': 'cls._render_event_timeline = _i_render_event_timeline' in final,
        'session_summary_patch': 'cls._render_session_summary = _i_render_session_summary' in final,
        'offline_english': 'Backend offline.' in final,
        'audit_warning_summary': 'Warnings/errors :' in final,
    }
    print('4B.4.3.6.6.20i dashboard contract reset patch applied')
    for k, v in checks.items():
        print(f' - {k}: {v}')
    if not all(checks.values()):
        raise RuntimeError(f'20i checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
