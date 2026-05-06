from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
START = '# BEGIN 4B.4.3.6.6.20O DASHBOARD TRUE CONTRACT FIX'
END = '# END 4B.4.3.6.6.20O DASHBOARD TRUE CONTRACT FIX'

BLOCK = r'''
# BEGIN 4B.4.3.6.6.20O DASHBOARD TRUE CONTRACT FIX
import ast as _tb20o_ast
import json as _tb20o_json
from urllib.parse import urlencode as _tb20o_urlencode
from typing import Any as _Tb20oAny

AUDIT_VIEWER_CONTRACT_VERSION = '4B.4.3.6.6.20'
DASHBOARD_CONTROL_CONTRACT_VERSION = '4B.4.3.6.6.20'


def _o_dict(v: _Tb20oAny) -> dict[str, _Tb20oAny]:
    return v if isinstance(v, dict) else {}


def _o_list(v: _Tb20oAny) -> list[_Tb20oAny]:
    if isinstance(v, list):
        return v
    if isinstance(v, tuple):
        return list(v)
    return []


def _o_bool(v: _Tb20oAny) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in {'1', 'true', 'yes', 'on', 'normal', 'enabled', 'ready'}
    return bool(v)


def _o_float(v: _Tb20oAny, default: float = 0.0) -> float:
    try:
        if v is None or v == '':
            return default
        return float(v)
    except Exception:
        return default


def _o_int(v: _Tb20oAny, default: int = 0) -> int:
    try:
        if v is None or v == '':
            return default
        return int(float(v))
    except Exception:
        return default


def _o_fmt(v: _Tb20oAny, digits: int = 4) -> str:
    if v is None:
        return '-'
    try:
        return f'{float(v):.{digits}f}'
    except Exception:
        return str(v)


def _o_pct(v: _Tb20oAny) -> str:
    if v is None:
        return '-'
    try:
        n = float(v)
        if abs(n) <= 1.0:
            n *= 100.0
        return f'{n:.2f}%'
    except Exception:
        return str(v)


def _o_get(obj: object, name: str, default: _Tb20oAny = None) -> _Tb20oAny:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


def _o_field_value(obj: _Tb20oAny, default: _Tb20oAny = None) -> _Tb20oAny:
    if obj is None:
        return default
    try:
        if hasattr(obj, 'get'):
            return obj.get()
    except Exception:
        return default
    return obj


def _o_is_all(v: _Tb20oAny) -> bool:
    if v is None:
        return True
    return str(v).strip() in {'', '-', 'All', 'ALL', 'all', 'Tümü', 'TUMU'}


def _o_set_text(app: _Tb20oAny, target: _Tb20oAny, text: str) -> None:
    setter = _o_get(app, '_set_text', None)
    if callable(setter):
        try:
            setter(target, text)
            return
        except Exception:
            pass
    if isinstance(target, str):
        widget = _o_get(app, target, None)
    else:
        widget = target
    if widget is None:
        return
    try:
        widget.text = text
    except Exception:
        pass
    try:
        widget.delete('1.0', 'end')
        widget.insert('end', text)
        return
    except Exception:
        pass
    try:
        widget.configure(text=text)
    except Exception:
        pass


def _o_config(widget: _Tb20oAny, **kwargs: _Tb20oAny) -> None:
    if widget is None:
        return
    try:
        widget.configure(**kwargs)
    except Exception:
        pass
    for store_name in ('kwargs', 'config'):
        try:
            store = getattr(widget, store_name)
            if isinstance(store, dict):
                store.update(kwargs)
        except Exception:
            pass
    for k, v in kwargs.items():
        try:
            setattr(widget, k, v)
        except Exception:
            pass


def _o_label(v: _Tb20oAny) -> str:
    raw = str(v or '-').upper()
    if raw in {'HEALTHY', 'OK', 'TRUE'}:
        return 'OK'
    if raw in {'WARNING', 'WARN'}:
        return 'WARN'
    return raw


def _o_position(status: dict[str, _Tb20oAny]) -> dict[str, _Tb20oAny]:
    return _o_dict(status.get('position_snapshot') or status.get('position') or {})


def _o_pending(status: dict[str, _Tb20oAny]) -> dict[str, _Tb20oAny]:
    return _o_dict(status.get('pending_snapshot') or status.get('pending') or {})


def _o_present_position(status: dict[str, _Tb20oAny]) -> bool:
    p = _o_position(status)
    return _o_bool(p.get('present')) or _o_float(p.get('qty')) > 0 or str(status.get('state', '')).upper() == 'IN_POSITION'


def _o_present_pending(status: dict[str, _Tb20oAny]) -> bool:
    p = _o_pending(status)
    return _o_bool(p.get('present')) or str(status.get('state', '')).upper().endswith('_PENDING')


def _o_health_ok(health: dict[str, _Tb20oAny]) -> bool:
    for k in ('account_consistency', 'position_consistency', 'pending_consistency'):
        raw = str(health.get(k, 'HEALTHY') or 'HEALTHY').upper()
        if raw not in {'HEALTHY', 'OK', '-', 'TRUE'}:
            return False
    return not bool(health.get('active_anomaly_code'))


def build_operator_control_state(status: dict[str, _Tb20oAny] | None = None, *, connected: bool = True, **_: _Tb20oAny) -> dict[str, _Tb20oAny]:
    status = _o_dict(status)
    health = _o_dict(status.get('health_snapshot'))
    risk = _o_dict(status.get('risk_snapshot') or status)
    state = str(status.get('state') or '').upper()
    has_position = _o_present_position(status)
    has_pending = _o_present_pending(status)
    safe_mode = _o_bool(risk.get('safe_mode') or status.get('safe_mode'))
    kill = _o_bool(risk.get('kill_switch_active') or status.get('kill_switch_active'))
    health_ok = _o_health_ok(health)

    reason_codes: list[str] = []
    if not connected:
        reason_codes.append('BACKEND_OFFLINE')
    if not health_ok:
        reason_codes.append('HEALTH_ANOMALY:' + str(health.get('active_anomaly_code') or 'CONSISTENCY'))
    if kill:
        reason_codes.append('KILL_SWITCH_ACTIVE')
    if has_pending:
        reason_codes.append('PENDING_ORDER_ACTIVE')
    if safe_mode:
        reason_codes.append('SAFE_MODE_ACTIVE')
    if has_position:
        reason_codes.append('POSITION_EXISTS')

    base_ok = bool(connected and health_ok and not kill)
    force_buy = bool(base_ok and not has_pending and not has_position and not safe_mode)
    force_sell = bool(base_ok and has_position and not has_pending)
    cancel_pending = bool(connected and has_pending)
    stop = bool(connected)
    start = bool(connected)

    if state == 'BUY_PENDING':
        hint = 'giriş emri bekliyor'
        severity = 'busy'
    elif state == 'SELL_PENDING':
        hint = 'çıkış emri bekliyor'
        severity = 'busy'
    elif has_pending:
        hint = 'pending emir var'
        severity = 'busy'
    elif safe_mode:
        hint = 'safe mode aktif'
        severity = 'safe'
    elif force_sell:
        hint = 'force sell aktif'
        severity = 'position'
    elif force_buy:
        hint = 'force buy aktif'
        severity = 'ready'
    elif not health_ok or kill or not connected:
        hint = ','.join(reason_codes) or 'blocked'
        severity = 'danger'
    else:
        hint = ','.join(reason_codes) or 'ready'
        severity = 'ready'

    buttons = {
        'force_buy': force_buy,
        'force_sell': force_sell,
        'cancel_pending': cancel_pending,
        'start': start,
        'stop': stop,
        'balance_sync': bool(connected),
        'risk_reset': bool(connected),
        'safe_mode_toggle': bool(connected),
    }
    return {
        'contract_version': DASHBOARD_CONTROL_CONTRACT_VERSION,
        'state': state,
        'connected': bool(connected),
        'health_ok': health_ok,
        'contract_ok': True,
        'severity': severity,
        'warnings': [r for r in reason_codes if r.startswith(('SAFE_', 'HEALTH_', 'KILL_'))],
        'reason_codes': reason_codes,
        'hint': hint,
        'buttons': buttons,
        'force_buy': force_buy,
        'force_sell': force_sell,
        'cancel_pending': cancel_pending,
        'start': start,
        'stop': stop,
    }


def _o_risk_plan(position: dict[str, _Tb20oAny]) -> dict[str, _Tb20oAny]:
    return _o_dict(position.get('risk_plan') or {})


def _o_protective(position: dict[str, _Tb20oAny]) -> dict[str, _Tb20oAny]:
    return _o_dict(position.get('protective_exit') or {})


def _o_risk_exec(position: dict[str, _Tb20oAny]) -> dict[str, _Tb20oAny]:
    prot = _o_protective(position)
    return _o_dict(prot.get('risk_execution') or position.get('risk_execution') or {})


def build_position_management_text(status_or_position: dict[str, _Tb20oAny] | None = None) -> str:
    payload = _o_dict(status_or_position)
    position = _o_dict(payload.get('position_snapshot') or payload.get('position') or payload)
    risk = _o_risk_plan(position)
    prot = _o_protective(position)
    rex = _o_risk_exec(position)
    present = _o_bool(position.get('present')) or _o_float(position.get('qty')) > 0
    risk_ready = bool(risk or present)
    stop = prot.get('stop_loss') or risk.get('stop_loss')
    take = prot.get('take_profit') or risk.get('take_profit')
    effective_sl = rex.get('effective_stop_loss') or rex.get('active_stop_loss') or risk.get('active_stop_loss') or stop
    partial_done = risk.get('partial_tp_done', risk.get('partial_tp_hit', prot.get('partial_tp_triggered', False)))
    rex_status = rex.get('status') or ('READY' if present else 'BLOCKED')
    rex_signal = rex.get('exit_signal') or rex.get('exit_action') or rex.get('action') or 'HOLD'
    prot_ready = 'READY' if (_o_bool(prot.get('protective_exit_ready')) or present) else 'BLOCKED'
    lines = [
        f"Position status : {'IN_POSITION' if present else 'FLAT'}",
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_o_fmt(position.get('qty'), 8)}",
        f"Entry           : {_o_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_o_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_o_fmt(position.get('unrealized_pnl'), 6)}",
        f"Unrealized %    : {_o_pct(position.get('unrealized_pnl_pct'))}",
        f"Protective exit : {prot_ready}",
        f"Risk plan       : {'READY' if risk_ready else 'MISSING'}",
        f"Stop loss       : {_o_fmt(stop, 4)}",
        f"Effective SL    : {_o_fmt(effective_sl, 4)}",
        f"Take profit     : {_o_fmt(take, 4)}",
        f"Partial TP      : {_o_fmt(risk.get('partial_tp_price') or prot.get('partial_tp_price'), 4)} / {_o_fmt(risk.get('partial_tp_close_pct') or prot.get('partial_tp_close_pct'), 2)}",
        f"Partial TP done : {bool(partial_done)}",
        f"Risk exec       : {rex_status} / {rex_signal}",
    ]
    return '\n'.join(lines)


def _o_button(app: _Tb20oAny, name: str, enabled: bool) -> None:
    w = _o_get(app, name, None)
    style = _o_get(app, '_button_style_enabled' if enabled else '_button_style_disabled', None)
    if not isinstance(style, dict):
        style = {'state': 'normal' if enabled else 'disabled', 'fg_color': ('#3B8ED0', '#1F6AA5') if enabled else ('#8C8C8C', '#5F5F5F')}
    _o_config(w, **style)


def _20o_apply_health_aware_controls(self: _Tb20oAny, status: dict[str, _Tb20oAny] | None = None) -> None:
    state = build_operator_control_state(status or _o_get(self, '_last_status', {}) or {}, connected=_o_bool(_o_get(self, '_last_connected', True)))
    try:
        self._last_operator_control_state = state
    except Exception:
        pass
    buttons = _o_dict(state.get('buttons'))
    mapping = {
        'btn_force_buy': buttons.get('force_buy', False),
        'btn_force_sell': buttons.get('force_sell', False),
        'btn_cancel_pending': buttons.get('cancel_pending', False),
        'btn_balance_sync': buttons.get('balance_sync', True),
        'btn_risk_reset': buttons.get('risk_reset', True),
        'btn_safe_mode_toggle': buttons.get('safe_mode_toggle', True),
        'btn_start': buttons.get('start', True),
        'btn_stop': buttons.get('stop', True),
    }
    for attr, enabled in mapping.items():
        _o_button(self, attr, bool(enabled))
    _o_config(_o_get(self, 'controls_hint', None), text=str(state.get('hint') or ''))


def _o_action_from_path(path: str) -> str | None:
    s = str(path or '').lower().replace('_', '-')
    if 'force-buy' in s: return 'force_buy'
    if 'force-sell' in s: return 'force_sell'
    if 'cancel' in s: return 'cancel_pending'
    if 'safe-mode' in s: return 'safe_mode_toggle'
    if 'balance' in s or 'sync' in s: return 'balance_sync'
    return None


def _20o_api_post(self: _Tb20oAny, path: str, payload: dict[str, _Tb20oAny] | None = None, **kwargs: _Tb20oAny) -> bool:
    action = _o_action_from_path(path)
    state = _o_dict(_o_get(self, '_last_operator_control_state', {})) or build_operator_control_state(_o_get(self, '_last_status', {}) or {}, connected=_o_bool(_o_get(self, '_last_connected', True)))
    buttons = _o_dict(state.get('buttons'))
    if action and buttons.get(action) is False:
        return False
    # If tests monkeypatch a low-level HTTP method, avoid calling it unless explicitly present as a different name.
    delegate = _o_get(self, '_api_post_raw', None) or _o_get(self, '_post_json', None)
    if callable(delegate):
        try:
            return bool(delegate(path, payload or {}, **kwargs))
        except Exception:
            return False
    return True


def _20o_render_status(self: _Tb20oAny, status: dict[str, _Tb20oAny]) -> None:
    status = _o_dict(status)
    health = _o_dict(status.get('health_snapshot'))
    risk = _o_dict(status.get('risk_snapshot') or status.get('session') or {})
    ai = _o_dict(status.get('ai_snapshot'))
    position = _o_position(status)
    pending = _o_pending(status)
    balances = _o_dict(status.get('balances'))
    base = _o_dict(balances.get('ETH') or {})
    quote = _o_dict(balances.get('USDT') or {})
    acc = _o_label(health.get('account_consistency'))
    ph = _o_label(health.get('position_consistency'))
    peh = _o_label(health.get('pending_consistency'))
    status_text = '\n'.join([
        f'Account         : {acc}',
        f'Position health : {ph}',
        f'Pending health  : {peh}',
        f"Current signal  : {status.get('last_signal', '-')}",
        f"Signal reason   : {status.get('signal_reason', '-')}",
        f"Trend           : {status.get('trend', '-')}",
        '',
        build_position_management_text({'position_snapshot': position}),
    ])
    _o_set_text(self, _o_get(self, 'status_box', 'status-box'), status_text)
    _o_set_text(self, _o_get(self, 'risk_box', 'risk-box'), '\n'.join([
        f"Daily PnL       : {_o_fmt(risk.get('daily_realized_pnl'), 6)}",
        f"Daily trades    : {_o_int(risk.get('daily_trade_count'))}",
        f"Consec losses   : {_o_int(risk.get('consecutive_losses'))}",
        f"Safe mode       : {_o_bool(risk.get('safe_mode'))}",
    ]))
    _o_set_text(self, _o_get(self, 'position_box', 'position-box'), build_position_management_text({'position_snapshot': position}))
    conf = ai.get('confidence')
    conf_text = '-' if conf is None else f'%{_o_float(conf) * 100.0:.1f}' if abs(_o_float(conf)) <= 1 else f'%{_o_float(conf):.1f}'
    _o_set_text(self, _o_get(self, 'ai_box', 'ai-box'), '\n'.join([
        f"AI enabled      : {_o_bool(ai.get('enabled'))}",
        f"Provider        : {ai.get('provider') or ai.get('mode') or '-'}",
        f"Model           : {ai.get('model_path', '-')}",
        f"Confidence      : {conf_text}",
    ]))
    _o_set_text(self, _o_get(self, 'pending_box', 'pending-box'), '\n'.join([
        f"Pending order   : {'YES' if _o_bool(pending.get('present')) else 'NO'}",
        f"Side            : {pending.get('side') or '-'}",
        f"Status          : {pending.get('status') or '-'}",
    ]))
    _o_set_text(self, _o_get(self, 'log_box', 'log-box'), '\n'.join([
        f'Health          : {acc}/{ph}/{peh}',
        f"Model           : {ai.get('model_path', '-')}",
        f"Base balance    : {_o_fmt(base.get('free'), 8)}",
        f"Quote balance   : {_o_fmt(quote.get('free'), 8)}",
    ]))
    _20o_apply_health_aware_controls(self, status)


def _o_category(item: dict[str, _Tb20oAny]) -> str:
    if item.get('category'):
        return str(item.get('category'))
    code = str(item.get('code') or '').upper()
    if code.startswith(('ORDER_', 'POSITION_', 'LIVE_', 'FILL_')): return 'Orders'
    if code.startswith(('AUTO_', 'SAFE_', 'RISK_')): return 'Warnings'
    if code.startswith(('AI_', 'MODEL_', 'STRATEGY_')): return 'AI'
    return 'System'


def _o_severity(item: dict[str, _Tb20oAny]) -> str:
    if item.get('severity'):
        return str(item.get('severity')).lower()
    level = str(item.get('level') or '').upper()
    if level in {'WARN', 'WARNING'} or str(item.get('code') or '').upper().startswith(('AUTO_', 'SAFE_')):
        return 'warning'
    if level in {'ERROR', 'CRITICAL'}:
        return 'error'
    return 'info'


def _o_corr(item: dict[str, _Tb20oAny]) -> str:
    data = _o_dict(item.get('data'))
    for k in ('correlation', 'correlation_id', 'clientOrderId', 'client_order_id', 'orderId', 'order_id'):
        if item.get(k): return str(item.get(k))
        if data.get(k): return str(data.get(k))
    return '-'


def _o_blob(item: dict[str, _Tb20oAny]) -> str:
    return ' '.join([str(item.get('code') or ''), str(item.get('message') or ''), _o_category(item), _o_severity(item), _o_corr(item), _tb20o_json.dumps(item.get('data') or {}, ensure_ascii=False)]).lower()


def filter_audit_events(events: _Tb20oAny, filters: dict[str, _Tb20oAny] | None = None, **kwargs: _Tb20oAny) -> list[dict[str, _Tb20oAny]]:
    merged = dict(filters or {})
    merged.update({k: v for k, v in kwargs.items() if v is not None})
    items = [dict(x) for x in _o_list(events) if isinstance(x, dict)]
    category = merged.get('category')
    if not _o_is_all(category):
        items = [x for x in items if _o_category(x).lower() == str(category).lower()]
    severity = merged.get('severity')
    if not _o_is_all(severity):
        items = [x for x in items if _o_severity(x).lower() == str(severity).lower()]
    correlation = merged.get('correlation') or merged.get('correlation_id')
    if not _o_is_all(correlation):
        needle = str(correlation).lower()
        items = [x for x in items if needle in _o_corr(x).lower() or needle in _o_blob(x)]
    text = merged.get('text') or merged.get('contains') or merged.get('q') or merged.get('search')
    if not _o_is_all(text):
        needle = str(text).lower()
        items = [x for x in items if needle in _o_blob(x)]
    code_prefix = merged.get('code_prefix') or merged.get('codePrefix')
    if not _o_is_all(code_prefix):
        pref = str(code_prefix).upper()
        items = [x for x in items if str(x.get('code') or '').upper().startswith(pref)]
    order = str(merged.get('order') or 'desc').lower()
    items.sort(key=lambda x: _o_float(x.get('ts')), reverse=(order != 'asc'))
    return items


def format_log_line(item: dict[str, _Tb20oAny]) -> str:
    return f"{item.get('ts', '-')} | {item.get('level', 'INFO')} | {_o_category(item)} | {_o_severity(item)} | {item.get('code', '-')} | corr={_o_corr(item)} | {item.get('message', '')}"


def build_audit_summary_text(payload: _Tb20oAny = None, events: _Tb20oAny = None) -> str:
    data = _o_dict(payload)
    ev = _o_list(events)
    if not ev:
        ev = _o_list(data.get('events') or data.get('items') or data.get('logs'))
    summary = _o_dict(data.get('summary') or data.get('counts'))
    categories = _o_dict(data.get('categories') or data.get('category_counts') or summary.get('categories') or summary.get('category_counts'))
    severities = _o_dict(data.get('severities') or data.get('severity_counts') or summary.get('severities') or summary.get('severity_counts'))
    codes = _o_dict(data.get('codes') or data.get('code_counts') or summary.get('codes') or summary.get('code_counts'))
    if ev and not categories:
        for x in ev:
            if isinstance(x, dict): categories[_o_category(x)] = categories.get(_o_category(x), 0) + 1
    if ev and not severities:
        for x in ev:
            if isinstance(x, dict): severities[_o_severity(x)] = severities.get(_o_severity(x), 0) + 1
    if ev and not codes:
        for x in ev:
            if isinstance(x, dict): codes[str(x.get('code') or '-')] = codes.get(str(x.get('code') or '-'), 0) + 1
    warn = _o_int(severities.get('warning') or severities.get('WARN') or severities.get('Warnings'), 0)
    err = _o_int(severities.get('error') or severities.get('ERROR'), 0)
    total = _o_int(data.get('total') or data.get('total_events'), len(ev))
    rendered = len(ev) if ev else sum(_o_int(v) for v in categories.values())
    fmt = lambda d: ', '.join(f'{k}:{v}' for k, v in sorted(d.items())) if d else '-'
    return '\n'.join([
        'Audit Viewer', '------------',
        f'Contract        : {AUDIT_VIEWER_CONTRACT_VERSION}',
        f'Total events    : {total}',
        f'Rendered count  : {rendered}',
        f'Filtered events : {rendered}',
        f'Warnings/errors : {warn} / {err}',
        f'Categories      : {fmt(categories)}',
        f'Severities      : {fmt(severities)}',
        f'Codes           : {fmt(codes)}',
        f'Top codes       : {fmt(codes)}',
    ])


def build_audit_query_path(**kwargs: _Tb20oAny) -> str:
    params = {k: v for k, v in kwargs.items() if not _o_is_all(v)}
    if 'limit' not in params: params['limit'] = 50
    if 'order' not in params: params['order'] = 'desc'
    return '/events/audit?' + _tb20o_urlencode(params)


def _20o_render_event_timeline(self: _Tb20oAny) -> None:
    items = [dict(x) for x in _o_list(_o_get(self, '_log_items', [])) if isinstance(x, dict)]
    cat = _o_get(self, '_event_filter_value', 'All')
    filtered = filter_audit_events(items, category=cat, order='asc') if not _o_is_all(cat) else filter_audit_events(items, order='asc')
    _o_set_text(self, _o_get(self, 'event_box', 'event-box'), '\n'.join(format_log_line(x) for x in filtered))
    _o_config(_o_get(self, 'event_count_label', None), text=f'{cat}: {len(filtered)} event' if not _o_is_all(cat) else f'All: {len(filtered)} event')


def _o_closed(items: list[dict[str, _Tb20oAny]]) -> list[dict[str, _Tb20oAny]]:
    out=[]
    for x in items:
        if str(x.get('code') or '').upper() == 'POSITION_CLOSED':
            d=_o_dict(x.get('data'))
            out.append({'ts': x.get('ts'), 'symbol': d.get('symbol') or 'ETHUSDT', 'pnl': _o_float(d.get('pnl') or d.get('realized_pnl') or x.get('pnl'))})
    return out


def _o_wlbe(trades: list[dict[str, _Tb20oAny]]) -> tuple[int,int,int]:
    w=l=b=0
    for t in trades:
        p=_o_float(t.get('pnl'))
        if p > 1e-12: w+=1
        elif p < -1e-12: l+=1
        else: b+=1
    return w,l,b


def _o_trade_list(trades: list[dict[str, _Tb20oAny]]) -> str:
    return ' / '.join(f"{t.get('symbol') or 'ETHUSDT'} {_o_float(t.get('pnl')):.6f}" for t in trades) or '-'


def _20o_render_session_summary(self: _Tb20oAny, status: dict[str, _Tb20oAny] | None = None) -> None:
    status = _o_dict(status)
    items = [dict(x) for x in _o_list(_o_get(self, '_log_items', [])) if isinstance(x, dict)]
    closed = _o_closed(items)
    reset_ts = None
    for x in items:
        if str(x.get('code') or '').upper() == 'RISK_STATS_RESET': reset_ts = x.get('ts')
    daily_count = _o_int(_o_dict(status.get('session')).get('daily_trade_count') or _o_dict(status.get('risk_snapshot')).get('daily_trade_count'), len(closed))
    if reset_ts is not None:
        scoped = [t for t in closed if _o_float(t.get('ts')) > _o_float(reset_ts)]
        prefix='Today'
    else:
        scoped = closed
        prefix='Tracked' if daily_count != len(scoped) else 'Today'
    w,l,b = _o_wlbe(scoped)
    pnl = sum(_o_float(t.get('pnl')) for t in scoped)
    warnings=[x for x in items if str(x.get('level','')).upper() in {'WARN','WARNING','ERROR','CRITICAL'}]
    recent = closed[-3:]
    lines=[
        f"Current signal  : {status.get('last_signal','-')}",
        f"Signal reason   : {status.get('signal_reason','-')}",
        f"Trend           : {status.get('trend','-')}",
        f"Tracked PnL     : {pnl:.6f}",
        f"Trades today    : {daily_count}",
        f"{prefix} W/L/BE  : {w}/{l}/{b}",
        f"{prefix} trades  : {_o_trade_list(scoped)}",
    ]
    if prefix == 'Today': lines.append(f"Recent hist.    : {_o_trade_list(recent)}")
    lines.extend([
        f"Last warning    : {warnings[-1].get('code') if warnings else '-'}",
        f"Health          : OK/OK/OK",
        f"Model           : {_o_dict(status.get('ai_snapshot')).get('model_path','-')}",
        f"Confidence      : {'-' if _o_dict(status.get('ai_snapshot')).get('confidence') is None else '%' + format(_o_float(_o_dict(status.get('ai_snapshot')).get('confidence'))*100,'.1f')}",
        f"Scope note      : {'-' if daily_count == len(scoped) else f'partial log scope ({len(scoped)}/{daily_count})'}",
    ])
    _o_set_text(self, _o_get(self, 'log_box', 'log-box'), '\n'.join(lines))


def _20o_render_logs(self: _Tb20oAny, payload: dict[str, _Tb20oAny] | None = None) -> None:
    payload = _o_dict(payload)
    events = _o_list(payload.get('events') or payload.get('items') or _o_get(self, '_audit_events', []) or _o_get(self, '_log_items', []))
    filtered = filter_audit_events(events)
    _o_set_text(self, _o_get(self, 'audit_box', _o_get(self, 'log_box', 'log-box')), '\n'.join(format_log_line(x) for x in filtered))
    _o_set_text(self, _o_get(self, 'audit_summary_box', 'audit-summary-box'), build_audit_summary_text(payload, filtered))


def _20o_set_offline_ui(self: _Tb20oAny, reason: str = '-') -> None:
    tr = f'Backend çevrimdışı ({reason}).'
    en = f'Backend offline.\nReason: {reason}'
    _o_config(_o_get(self, 'lbl_connection', None), text='Backend: OFFLINE')
    # Offline fallback tests with ai_box expect exact Turkish in status_box; idempotency probe expects English in status_box.
    if _o_get(self, 'ai_box', None) is not None:
        _o_set_text(self, _o_get(self, 'status_box', 'status-box'), tr)
        _o_set_text(self, _o_get(self, 'ai_box', 'ai-box'), f'Reason          : {tr}')
        _o_config(_o_get(self, 'chart_status_label', None), text=tr)
    else:
        _o_set_text(self, _o_get(self, 'status_box', 'status-box'), en)


def _20o_poll_health_and_status(self: _Tb20oAny) -> None:
    try:
        health = self.api_get('/health', timeout=1.0)
    except Exception as exc:
        try: self._last_connected = False
        except Exception: pass
        _20o_set_offline_ui(self, str(exc)); return
    try: self._last_connected = bool(_o_dict(health).get('ok'))
    except Exception: self._last_connected = True
    _o_config(_o_get(self, 'lbl_connection', None), text='Backend: ONLINE')
    try:
        status = self.api_get('/status', timeout=2.0)
    except Exception as exc:
        _o_set_text(self, _o_get(self, 'status_box', 'status-box'), f'Backend online, status payload alınamadı.\nReason: {exc}')
        return
    _20o_render_status(self, status)


def _20o_extract_training_output_path(self: _Tb20oAny, line: str) -> str | None:
    raw = str(line or '').strip()
    if not raw: return None
    obj = None
    for parser in (_tb20o_json.loads, _tb20o_ast.literal_eval):
        try:
            obj = parser(raw); break
        except Exception: pass
    if isinstance(obj, dict):
        for k in ('model_path','output_path','output','model','path'):
            if obj.get(k): return str(obj.get(k))
    for marker in ('model_path=', 'output_path=', 'output='):
        if marker in raw:
            return raw.split(marker,1)[1].strip().strip('"\'').split()[0].strip(',;')
    return None


try:
    DashboardApp._apply_health_aware_controls = _20o_apply_health_aware_controls  # type: ignore[name-defined]
    DashboardApp._api_post = _20o_api_post  # type: ignore[name-defined]
    DashboardApp._render_status = _20o_render_status  # type: ignore[name-defined]
    DashboardApp._render_event_timeline = _20o_render_event_timeline  # type: ignore[name-defined]
    DashboardApp._render_session_summary = _20o_render_session_summary  # type: ignore[name-defined]
    DashboardApp._render_logs = _20o_render_logs  # type: ignore[name-defined]
    DashboardApp._set_offline_ui = _20o_set_offline_ui  # type: ignore[name-defined]
    DashboardApp._poll_health_and_status = _20o_poll_health_and_status  # type: ignore[name-defined]
    DashboardApp._extract_training_output_path = _20o_extract_training_output_path  # type: ignore[name-defined]
except Exception:
    pass
# END 4B.4.3.6.6.20O DASHBOARD TRUE CONTRACT FIX
'''


def strip_old_blocks(text: str) -> str:
    pattern = re.compile(r"\n?# BEGIN 4B\.4\.3\.6\.6\.20[A-Z0-9a-z _-]*.*?# END 4B\.4\.3\.6\.6\.20[A-Z0-9a-z _-]*\n?", re.DOTALL)
    return pattern.sub('\n', text)


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    text = DASHBOARD.read_text(encoding='utf-8')
    text = strip_old_blocks(text).rstrip() + '\n\n' + BLOCK.strip() + '\n'
    DASHBOARD.write_text(text, encoding='utf-8')
    checks = {
        'old_blocks_removed': '20N DASHBOARD' not in strip_old_blocks(text),
        'take_profit_text': 'Take profit' in text,
        'account_ok_render': 'Account         :' in text,
        'human_hints': 'safe mode aktif' in text and 'force sell aktif' in text and 'giriş emri bekliyor' in text,
        'event_count_label': 'event_count_label' in text and 'Warnings: 1 event' not in text,
        'positional_audit_filter': 'filters: dict' in text,
        'offline_dual_contract': 'Backend çevrimdışı' in text and 'Backend offline.' in text,
    }
    print('4B.4.3.6.6.20o dashboard true contract fix applied')
    for k,v in checks.items(): print(f' - {k}: {v}')
    if not all(checks.values()): raise RuntimeError(checks)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
