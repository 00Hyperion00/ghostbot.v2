from __future__ import annotations

from pathlib import Path

START = '# BEGIN 4B.4.3.6.6.20F DASHBOARD ROOT CONTRACT RESTORE'
END = '# END 4B.4.3.6.6.20F DASHBOARD ROOT CONTRACT RESTORE'

COMPAT_BLOCK = r'''
# BEGIN 4B.4.3.6.6.20F DASHBOARD ROOT CONTRACT RESTORE
# Final root restore for dashboard helper contracts broken by 20/20a/20b/20c/20d/20e.
# Scope: dashboard.py only. No engine/API/order/risk/model code is changed.
import json as _tb20f_json
from urllib.parse import urlencode as _tb20f_urlencode
from typing import Any as _Tb20fAny

AUDIT_VIEWER_CONTRACT_VERSION = '4B.4.3.6.6.20'
DASHBOARD_CONTROL_CONTRACT_VERSION = '4B.4.3.6.6.20'


def _tb20f_dict(value: _Tb20fAny) -> dict[str, _Tb20fAny]:
    return value if isinstance(value, dict) else {}


def _tb20f_list(value: _Tb20fAny) -> list[_Tb20fAny]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _tb20f_get(obj: _Tb20fAny, name: str, default: _Tb20fAny = None) -> _Tb20fAny:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


safe_obj_getattr = _tb20f_get  # hard alias; fixes prior safe_obj_safe_obj_getattr fallout too


def _tb20f_bool(value: _Tb20fAny) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on', 'enabled', 'ready', 'normal', 'ok', 'healthy'}
    return bool(value)


def _tb20f_float(value: _Tb20fAny, default: float = 0.0) -> float:
    try:
        if value is None or value == '':
            return default
        return float(value)
    except Exception:
        return default


def _tb20f_int(value: _Tb20fAny, default: int = 0) -> int:
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except Exception:
        return default


def _tb20f_fmt(value: _Tb20fAny, digits: int = 4) -> str:
    try:
        if value is None:
            return '-'
        return f'{float(value):.{digits}f}'
    except Exception:
        return '-' if value in (None, '') else str(value)


def _tb20f_pct(value: _Tb20fAny) -> str:
    try:
        if value is None:
            return '-'
        numeric = float(value)
        if abs(numeric) <= 1.0:
            numeric *= 100.0
        return f'{numeric:.2f}%'
    except Exception:
        return '-' if value in (None, '') else str(value)


def _tb20f_is_all(value: _Tb20fAny) -> bool:
    if value is None:
        return True
    raw = str(value).strip()
    return raw in {'', '-', 'All', 'ALL', 'all', 'Tümü', 'TUMU', 'Tümü / All'}


def _tb20f_var(obj: _Tb20fAny, default: _Tb20fAny = None) -> _Tb20fAny:
    if obj is None:
        return default
    try:
        if hasattr(obj, 'get') and callable(obj.get):
            return obj.get()
    except Exception:
        pass
    return obj


def _tb20f_health_label(value: _Tb20fAny) -> str:
    raw = str(value or '-').upper()
    if raw in {'HEALTHY', 'OK', 'TRUE'}:
        return 'OK'
    if raw in {'WARNING', 'WARN'}:
        return 'WARN'
    if raw in {'ERROR', 'BROKEN', 'LOCKED', 'UNHEALTHY'}:
        return raw
    return raw


def _tb20f_health_ok(health: dict[str, _Tb20fAny]) -> bool:
    if health.get('active_anomaly_code'):
        return False
    for key in ('account_consistency', 'position_consistency', 'pending_consistency'):
        raw = str(health.get(key, 'HEALTHY') or 'HEALTHY').upper()
        if raw not in {'HEALTHY', 'OK', 'TRUE', '-'}:
            return False
    return True


def _tb20f_contract_stale(version: _Tb20fAny) -> bool:
    raw = str(version or '')
    if not raw.startswith('4B.4.3.6.6.'):
        return False
    try:
        return int(raw.rsplit('.', 1)[-1]) < 7
    except Exception:
        return False


def _tb20f_position(status: dict[str, _Tb20fAny]) -> dict[str, _Tb20fAny]:
    return _tb20f_dict(status.get('position_snapshot') or status.get('position') or {})


def _tb20f_pending(status: dict[str, _Tb20fAny]) -> dict[str, _Tb20fAny]:
    return _tb20f_dict(status.get('pending_snapshot') or status.get('pending') or {})


def _tb20f_has_position(status: dict[str, _Tb20fAny]) -> bool:
    position = _tb20f_position(status)
    state = str(status.get('state') or '').upper()
    return bool(_tb20f_bool(position.get('present')) or _tb20f_float(position.get('qty')) > 0 or state.endswith('IN_POSITION'))


def _tb20f_has_pending(status: dict[str, _Tb20fAny]) -> bool:
    pending = _tb20f_pending(status)
    state = str(status.get('state') or '').upper()
    return bool(_tb20f_bool(pending.get('present')) or state in {'BUY_PENDING', 'SELL_PENDING'} or state.endswith('_PENDING'))


def _tb20f_protective_blocked(position: dict[str, _Tb20fAny]) -> tuple[bool, str | None]:
    protective = _tb20f_dict(position.get('protective_exit'))
    if not protective:
        return False, None
    reason = protective.get('block_reason')
    if reason and str(reason).upper() not in {'-', 'NONE', 'OK', 'READY'}:
        return True, str(reason).upper()
    if protective.get('protective_exit_ready') is False:
        return True, 'PROTECTIVE_EXIT_NOT_READY'
    return False, None


def build_operator_control_state(status: dict[str, _Tb20fAny] | None = None, *, connected: bool = True, **_: _Tb20fAny) -> dict[str, _Tb20fAny]:
    status = _tb20f_dict(status)
    state = str(status.get('state') or status.get('runtime_state') or 'FLAT')
    health = _tb20f_dict(status.get('health_snapshot'))
    risk = _tb20f_dict(status.get('risk_snapshot') or status)
    position = _tb20f_position(status)
    has_position = _tb20f_has_position(status)
    has_pending = _tb20f_has_pending(status)
    safe_mode = _tb20f_bool(risk.get('safe_mode') or status.get('safe_mode'))
    kill_switch = _tb20f_bool(risk.get('kill_switch_active') or status.get('kill_switch_active'))
    health_ok = _tb20f_health_ok(health)
    stale = _tb20f_contract_stale(status.get('contract_version'))
    protective_blocked, protective_reason = _tb20f_protective_blocked(position)

    common: list[str] = []
    if not connected:
        common.append('BACKEND_OFFLINE')
    if stale:
        common.append('STALE_CONTRACT')
    if not health_ok:
        common.append('HEALTH_ANOMALY')
    if kill_switch:
        common.append('KILL_SWITCH_ACTIVE')

    buy_reasons = list(common)
    if safe_mode:
        buy_reasons.append('SAFE_MODE_ACTIVE')
    if has_pending:
        buy_reasons.append('PENDING_ORDER_EXISTS')
    if has_position:
        buy_reasons.append('POSITION_EXISTS')

    sell_reasons = list(common)
    if has_pending:
        sell_reasons.append('PENDING_ORDER_EXISTS')
    if not has_position:
        sell_reasons.append('POSITION_NOT_FOUND')
    if protective_blocked:
        sell_reasons.append(protective_reason or 'PROTECTIVE_EXIT_BLOCKED')

    cancel_reasons = [] if (connected and has_pending) else (['BACKEND_OFFLINE'] if not connected else ['PENDING_NOT_FOUND'])

    buttons = {
        'start': bool(connected and not _tb20f_bool(status.get('engine_running', status.get('running', True)))),
        'stop': bool(connected and _tb20f_bool(status.get('engine_running', status.get('running', True)))),
        'force_buy': not buy_reasons,
        'force_sell': not sell_reasons,
        'cancel_pending': not cancel_reasons,
        'balance_sync': bool(connected),
        'risk_reset': bool(connected),
        'safe_mode_toggle': bool(connected),
    }

    state_upper = state.upper()
    if state_upper == 'BUY_PENDING':
        hint = 'giriş emri bekliyor'
    elif state_upper == 'SELL_PENDING':
        hint = 'çıkış emri bekliyor'
    elif has_pending:
        hint = 'pending emir var'
    elif buttons['force_sell']:
        hint = 'force sell aktif'
    elif safe_mode:
        hint = 'safe mode aktif'
    elif not health_ok:
        hint = 'health anomaly'
    elif stale:
        hint = 'stale contract'
    elif buttons['force_buy']:
        hint = 'force buy aktif'
    else:
        hint = ','.join(dict.fromkeys(buy_reasons + sell_reasons + cancel_reasons)) or 'operator controls hazır'

    return {
        'contract_version': DASHBOARD_CONTROL_CONTRACT_VERSION,
        'connected': bool(connected),
        'state': state,
        'has_position': has_position,
        'has_pending': has_pending,
        'safe_mode': safe_mode,
        'kill_switch_active': kill_switch,
        'health_ok': health_ok,
        'stale_contract': stale,
        'protective_exit_blocked': protective_blocked,
        'buttons': buttons,
        'button_reasons': {
            'force_buy': ','.join(buy_reasons) if buy_reasons else None,
            'force_sell': ','.join(sell_reasons) if sell_reasons else None,
            'cancel_pending': ','.join(cancel_reasons) if cancel_reasons else None,
        },
        'hint': hint,
        # legacy direct booleans
        'force_buy': buttons['force_buy'],
        'force_sell': buttons['force_sell'],
        'cancel_pending': buttons['cancel_pending'],
        'safe_mode_toggle': buttons['safe_mode_toggle'],
    }


def _tb20f_widget_text(app: _Tb20fAny, widget: _Tb20fAny, text: str) -> None:
    setter = _tb20f_get(app, '_set_text', None)
    if callable(setter):
        try:
            setter(widget, text)
            return
        except Exception:
            pass
    if widget is None:
        return
    try:
        object.__setattr__(widget, 'text', text)
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
        widget.configure(text=text)
    except Exception:
        pass


def _tb20f_cfg(widget: _Tb20fAny, **kwargs: _Tb20fAny) -> None:
    if widget is None:
        return
    try:
        widget.configure(**kwargs)
    except Exception:
        pass
    try:
        current = _tb20f_get(widget, 'kwargs', None)
        if isinstance(current, dict):
            current.update(kwargs)
    except Exception:
        pass


def _tb20f_set_button_enabled(self: _Tb20fAny, button: _Tb20fAny, enabled: bool) -> None:
    style = _tb20f_dict(_tb20f_get(self, '_button_style_enabled' if enabled else '_button_style_disabled', {}))
    if not style:
        style = {
            'state': 'normal' if enabled else 'disabled',
            'fg_color': ('#3B8ED0', '#1F6AA5') if enabled else ('#8C8C8C', '#5F5F5F'),
            'hover_color': ('#36719F', '#144870') if enabled else ('#8C8C8C', '#5F5F5F'),
            'text_color': ('#FFFFFF', '#FFFFFF') if enabled else ('#E8E8E8', '#D8D8D8'),
            'text_color_disabled': ('#FFFFFF', '#FFFFFF') if enabled else ('#E8E8E8', '#D8D8D8'),
            'hover': bool(enabled),
        }
    _tb20f_cfg(button, **style)


def _tb20f_apply_health_aware_controls(self: _Tb20fAny, status: dict[str, _Tb20fAny]) -> None:
    controls = build_operator_control_state(status, connected=bool(_tb20f_get(self, '_last_connected', True)))
    try:
        self._last_operator_control_state = controls
    except Exception:
        pass
    buttons = _tb20f_dict(controls.get('buttons'))
    for attr, key in {
        'btn_start': 'start',
        'btn_stop': 'stop',
        'btn_force_buy': 'force_buy',
        'btn_force_sell': 'force_sell',
        'btn_cancel_pending': 'cancel_pending',
        'btn_balance_sync': 'balance_sync',
        'btn_risk_reset': 'risk_reset',
        'btn_safe_mode_toggle': 'safe_mode_toggle',
    }.items():
        _tb20f_set_button_enabled(self, _tb20f_get(self, attr, None), bool(buttons.get(key)))
    hint = str(controls.get('hint') or '-')
    _tb20f_cfg(_tb20f_get(self, 'controls_hint', None), text=hint)


def _tb20f_endpoint_action(path: str) -> str | None:
    raw = str(path or '').lower().replace('_', '-')
    if 'force-buy' in raw:
        return 'force_buy'
    if 'force-sell' in raw:
        return 'force_sell'
    if 'cancel' in raw:
        return 'cancel_pending'
    if 'safe-mode' in raw:
        return 'safe_mode_toggle'
    return None


def _tb20f_api_post(self: _Tb20fAny, path: str, payload: dict[str, _Tb20fAny] | None = None, **kwargs: _Tb20fAny) -> bool:
    action = _tb20f_endpoint_action(path)
    controls = _tb20f_dict(_tb20f_get(self, '_last_operator_control_state', {}))
    if not controls:
        controls = build_operator_control_state(_tb20f_dict(_tb20f_get(self, '_last_status', {})), connected=bool(_tb20f_get(self, '_last_connected', True)))
    buttons = _tb20f_dict(controls.get('buttons'))
    if action and buttons.get(action) is False:
        append = _tb20f_get(self, '_append_backend', None)
        if callable(append):
            try:
                append(f'Operator action blocked: {action}')
            except Exception:
                pass
        return False
    delegate = _tb20f_get(self, 'api_post', None)
    if callable(delegate) and delegate is not _tb20f_api_post:
        try:
            delegate(path, payload or {}, **kwargs)
            return True
        except Exception:
            return False
    return True


def _tb20f_risk_exec(position: dict[str, _Tb20fAny]) -> dict[str, _Tb20fAny]:
    protective = _tb20f_dict(position.get('protective_exit'))
    return _tb20f_dict(position.get('risk_execution') or protective.get('risk_execution') or {})


def build_position_management_text(status_or_position: dict[str, _Tb20fAny] | None = None) -> str:
    payload = _tb20f_dict(status_or_position)
    position = _tb20f_dict(payload.get('position_snapshot') or payload.get('position') or payload)
    protective = _tb20f_dict(position.get('protective_exit'))
    risk_plan = _tb20f_dict(position.get('risk_plan'))
    risk_exec = _tb20f_risk_exec(position)
    present = _tb20f_bool(position.get('present')) or _tb20f_float(position.get('qty')) > 0
    protective_ready = _tb20f_bool(protective.get('protective_exit_ready')) or (present and not protective.get('block_reason'))
    protective_label = 'READY' if protective_ready else f'BLOCKED / {protective.get("block_reason") or "POSITION_NOT_FOUND"}'
    effective_sl = risk_exec.get('effective_stop_loss') or risk_exec.get('active_stop_loss') or protective.get('active_stop_loss') or protective.get('stop_loss') or risk_plan.get('active_stop_loss') or risk_plan.get('stop_loss')
    partial_done = risk_exec.get('partial_tp_done')
    if partial_done is None:
        partial_done = risk_plan.get('partial_tp_done', risk_plan.get('partial_tp_hit', protective.get('partial_tp_done', False)))
    exec_status = risk_exec.get('status') or ('READY' if protective_ready else 'BLOCKED')
    exec_signal = risk_exec.get('exit_signal') or risk_exec.get('exit_action') or 'HOLD'
    lines = [
        f"Position status : {'IN_POSITION' if present else 'FLAT'}",
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_tb20f_fmt(position.get('qty'), 8)}",
        f"Entry           : {_tb20f_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_tb20f_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_tb20f_fmt(position.get('unrealized_pnl'), 6)}",
        f"Unrealized %    : {_tb20f_pct(position.get('unrealized_pnl_pct'))}",
        f"Protective exit : {protective_label}",
        f"Exit qty        : {_tb20f_fmt(protective.get('tradable_exit_qty'), 8)}",
        f"Exit notional   : {_tb20f_fmt(protective.get('exit_notional'), 4)}",
        f"Dust position   : {'YES' if _tb20f_bool(protective.get('is_dust')) else 'NO'}",
        f"Risk plan       : {'READY' if risk_plan else 'MISSING'}",
        f"Stop loss       : {_tb20f_fmt(protective.get('stop_loss') or risk_plan.get('stop_loss'), 4)}",
        f"Effective SL    : {_tb20f_fmt(effective_sl, 4)}",
        f"Active stop     : {_tb20f_fmt(risk_exec.get('active_stop_loss') or risk_plan.get('active_stop_loss') or effective_sl, 4)}",
        f"Take profit     : {_tb20f_fmt(protective.get('take_profit') or risk_plan.get('take_profit'), 4)}",
        f"Dist. to SL     : {_tb20f_fmt(protective.get('distance_to_stop'), 4)} ({_tb20f_pct(protective.get('distance_to_stop_pct'))})",
        f"Dist. to TP     : {_tb20f_fmt(protective.get('distance_to_take_profit'), 4)} ({_tb20f_pct(protective.get('distance_to_take_profit_pct'))})",
        f"Break-even      : {_tb20f_bool(risk_exec.get('break_even_armed') or risk_plan.get('break_even_moved') or risk_plan.get('break_even_armed'))} / trg {_tb20f_fmt(risk_plan.get('break_even_trigger_price'), 4)}",
        f"Trailing        : {_tb20f_bool(risk_plan.get('trailing_enabled'))} / armed {_tb20f_bool(risk_exec.get('trailing_armed') or risk_plan.get('trailing_armed'))} / stop {_tb20f_fmt(risk_exec.get('trailing_stop') or risk_plan.get('trailing_stop'), 4)}",
        f"Partial TP      : {_tb20f_fmt(risk_plan.get('partial_tp_price') or protective.get('partial_tp_price'), 4)} / {_tb20f_fmt(risk_plan.get('partial_tp_close_pct') or protective.get('partial_tp_close_pct'), 2)} / hit {_tb20f_bool(partial_done)}",
        f"Partial TP done : {_tb20f_bool(partial_done)}",
        f"Risk exec       : {exec_status} / {exec_signal}",
        f"Risk exit       : {risk_exec.get('exit_action') or 'NONE'} / {risk_exec.get('exit_reason') or '-'}",
    ]
    return '\n'.join(lines)


def _tb20f_norm_level(value: _Tb20fAny) -> str:
    raw = str(value or '').strip().upper()
    return 'WARN' if raw == 'WARNING' else raw


def _tb20f_event_category(item: dict[str, _Tb20fAny]) -> str:
    raw = item.get('category')
    if raw and not _tb20f_is_all(raw):
        return str(raw)
    code = str(item.get('code') or '').upper()
    if code.startswith(('ORDER_', 'LIVE_', 'FILL_', 'ENTRY_ORDER', 'EXIT_ORDER')):
        return 'Orders'
    if code.startswith(('AUTO_', 'ENTRY_GUARD', 'EXIT_GUARD')):
        return 'Guards'
    if code.startswith(('RISK_', 'SAFE_', 'KILL_')):
        return 'Warnings'
    if code.startswith(('AI_', 'MODEL_', 'STRATEGY_')):
        return 'AI'
    return 'Runtime'


def _tb20f_event_severity(item: dict[str, _Tb20fAny]) -> str:
    raw = item.get('severity')
    if raw and not _tb20f_is_all(raw):
        return str(raw).strip().lower()
    level = _tb20f_norm_level(item.get('level'))
    if level in {'ERROR', 'CRITICAL'}:
        return 'error'
    if level == 'WARN':
        return 'warning'
    return 'info'


def _tb20f_corr(item: dict[str, _Tb20fAny]) -> str:
    data = _tb20f_dict(item.get('data'))
    for key in ('correlation_id', 'correlationId', 'clientOrderId', 'client_order_id', 'orderId', 'order_id', 'signalKey', 'signal_key'):
        if item.get(key):
            return str(item.get(key))
        if data.get(key):
            return str(data.get(key))
    return '-'


def _tb20f_blob(item: dict[str, _Tb20fAny]) -> str:
    return ' '.join([
        str(item.get('level') or ''), str(item.get('code') or ''), str(item.get('message') or ''),
        _tb20f_event_category(item), _tb20f_event_severity(item), _tb20f_corr(item),
        _tb20f_json.dumps(item.get('data') or {}, ensure_ascii=False, sort_keys=True),
    ]).lower()


def _tb20f_format_ts(value: _Tb20fAny) -> str:
    try:
        import datetime as _dt
        ts = float(value or 0)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return _dt.datetime.fromtimestamp(ts).strftime('%d.%m.%Y %H:%M:%S')
    except Exception:
        return '-'


def format_log_line(item: dict[str, _Tb20fAny]) -> str:
    item = _tb20f_dict(item)
    return (
        f"{_tb20f_format_ts(item.get('ts'))} | {_tb20f_norm_level(item.get('level') or 'INFO'):<5} | "
        f"{_tb20f_event_category(item):<8} | {_tb20f_event_severity(item):<7} | {str(item.get('code') or '-'):<22} | "
        f"corr={_tb20f_corr(item)} | {item.get('message') or str(item.get('code') or '-')} | {_tb20f_dict(item.get('data'))}"
    )


def build_audit_query_path(*, limit: int = 50, order: str = 'desc', level: _Tb20fAny = None, code: _Tb20fAny = None, code_prefix: _Tb20fAny = None, contains: _Tb20fAny = None, q: _Tb20fAny = None, text: _Tb20fAny = None, search: _Tb20fAny = None, category: _Tb20fAny = None, severity: _Tb20fAny = None, correlation: _Tb20fAny = None, since_ts: _Tb20fAny = None, until_ts: _Tb20fAny = None, offset: _Tb20fAny = None, cursor: _Tb20fAny = None, **_: _Tb20fAny) -> str:
    params: dict[str, _Tb20fAny] = {'limit': int(limit), 'order': str(order or 'desc').lower()}
    if not _tb20f_is_all(level): params['level'] = _tb20f_norm_level(level)
    if not _tb20f_is_all(code): params['code'] = str(code).strip().upper()
    if not _tb20f_is_all(code_prefix): params['code_prefix'] = str(code_prefix).strip().upper()
    if not _tb20f_is_all(category): params['category'] = str(category).strip()
    if not _tb20f_is_all(severity): params['severity'] = str(severity).strip().lower()
    if not _tb20f_is_all(correlation): params['correlation'] = str(correlation).strip()
    query = q if not _tb20f_is_all(q) else (contains if not _tb20f_is_all(contains) else (text if not _tb20f_is_all(text) else search))
    if not _tb20f_is_all(query): params['q'] = str(query).strip()
    if since_ts not in (None, ''): params['since_ts'] = since_ts
    if until_ts not in (None, ''): params['until_ts'] = until_ts
    if offset not in (None, ''): params['offset'] = int(float(offset))
    if cursor not in (None, ''): params['cursor'] = str(cursor)
    return '/events/audit?' + _tb20f_urlencode(params)


def filter_audit_events(events: _Tb20fAny, *, level: _Tb20fAny = None, code: _Tb20fAny = None, code_prefix: _Tb20fAny = None, contains: _Tb20fAny = None, q: _Tb20fAny = None, text: _Tb20fAny = None, search: _Tb20fAny = None, category: _Tb20fAny = None, severity: _Tb20fAny = None, correlation: _Tb20fAny = None, since_ts: _Tb20fAny = None, until_ts: _Tb20fAny = None, limit: _Tb20fAny = None, offset: _Tb20fAny = 0, order: str = 'desc', **_: _Tb20fAny) -> list[dict[str, _Tb20fAny]]:
    filtered = [dict(item) for item in _tb20f_list(events) if isinstance(item, dict)]
    if not _tb20f_is_all(level):
        wanted = _tb20f_norm_level(level); filtered = [item for item in filtered if _tb20f_norm_level(item.get('level')) == wanted]
    if not _tb20f_is_all(code):
        wanted_code = str(code).strip().upper(); filtered = [item for item in filtered if str(item.get('code') or '').upper() == wanted_code]
    if not _tb20f_is_all(code_prefix):
        prefix = str(code_prefix).strip().upper(); filtered = [item for item in filtered if str(item.get('code') or '').upper().startswith(prefix)]
    if not _tb20f_is_all(category):
        wanted_category = str(category).strip().lower(); filtered = [item for item in filtered if _tb20f_event_category(item).lower() == wanted_category]
    if not _tb20f_is_all(severity):
        wanted_severity = str(severity).strip().lower(); filtered = [item for item in filtered if _tb20f_event_severity(item) == wanted_severity]
    if not _tb20f_is_all(correlation):
        wanted_corr = str(correlation).strip().lower(); filtered = [item for item in filtered if wanted_corr in _tb20f_corr(item).lower() or wanted_corr in _tb20f_blob(item)]
    query = q if not _tb20f_is_all(q) else (contains if not _tb20f_is_all(contains) else (text if not _tb20f_is_all(text) else search))
    if not _tb20f_is_all(query):
        needle = str(query).strip().lower(); filtered = [item for item in filtered if needle in _tb20f_blob(item)]
    if since_ts not in (None, ''):
        since = _tb20f_float(since_ts); filtered = [item for item in filtered if _tb20f_float(item.get('ts')) >= since]
    if until_ts not in (None, ''):
        until = _tb20f_float(until_ts); filtered = [item for item in filtered if _tb20f_float(item.get('ts')) <= until]
    filtered.sort(key=lambda item: _tb20f_float(item.get('ts')), reverse=str(order or 'desc').lower() != 'asc')
    start = max(0, _tb20f_int(offset, 0))
    if limit is None:
        return filtered[start:]
    return filtered[start:start + max(0, _tb20f_int(limit, len(filtered)))]


def _tb20f_extract_events(payload: _Tb20fAny, logs: _Tb20fAny = None) -> tuple[list[dict[str, _Tb20fAny]], int]:
    if logs is not None:
        events = [dict(item) for item in _tb20f_list(logs) if isinstance(item, dict)]
        total = len(events)
        if isinstance(payload, dict):
            total = _tb20f_int(payload.get('total', payload.get('total_events', total)), total)
        return events, total
    if isinstance(payload, list):
        events = [dict(item) for item in payload if isinstance(item, dict)]
        return events, len(events)
    data = _tb20f_dict(payload)
    raw = data.get('filtered_events') or data.get('events') or data.get('items') or data.get('logs') or data.get('recent') or []
    events = [dict(item) for item in _tb20f_list(raw) if isinstance(item, dict)]
    return events, _tb20f_int(data.get('total', data.get('total_events', data.get('count', len(events)))), len(events))


def build_audit_summary_text(payload: _Tb20fAny = None, logs: _Tb20fAny = None, **_: _Tb20fAny) -> str:
    events, total = _tb20f_extract_events(payload, logs)
    levels: dict[str, int] = {}; categories: dict[str, int] = {}; severities: dict[str, int] = {}; codes: dict[str, int] = {}
    warning_count = 0; error_count = 0
    for item in events:
        level = _tb20f_norm_level(item.get('level') or 'INFO')
        category = _tb20f_event_category(item); severity = _tb20f_event_severity(item); code = str(item.get('code') or '-')
        levels[level] = levels.get(level, 0) + 1; categories[category] = categories.get(category, 0) + 1; severities[severity] = severities.get(severity, 0) + 1; codes[code] = codes.get(code, 0) + 1
        if severity == 'warning': warning_count += 1
        if severity == 'error': error_count += 1
    fmt = lambda d: ', '.join(f'{k}:{v}' for k, v in sorted(d.items())) if d else '-'
    top_codes = ', '.join(f'{k}:{v}' for k, v in sorted(codes.items(), key=lambda kv: (-kv[1], kv[0]))[:8]) if codes else '-'
    return '\n'.join([
        'Audit Viewer', '------------',
        f'Contract        : {AUDIT_VIEWER_CONTRACT_VERSION}',
        f'Total events    : {total}',
        f'Rendered count  : {len(events)}',
        f'Filtered events : {len(events)}',
        f'Warnings/errors : {warning_count} / {error_count}',
        f'Levels          : {fmt(levels)}',
        f'Categories      : {fmt(categories)}',
        f'Severities      : {fmt(severities)}',
        f'Top codes       : {top_codes}',
    ])


def _tb20f_collect_audit_events(app: _Tb20fAny) -> list[dict[str, _Tb20fAny]]:
    for name in ('_audit_events', '_last_audit_events', 'audit_events', '_log_items', '_last_logs', 'logs'):
        value = _tb20f_get(app, name, None)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    payload = _tb20f_dict(_tb20f_get(app, '_last_audit_payload', {}))
    events, _ = _tb20f_extract_events(payload)
    return events


def _tb20f_get_filter(app: _Tb20fAny, *names: str, default: _Tb20fAny = None) -> _Tb20fAny:
    for name in names:
        obj = _tb20f_get(app, name, None)
        if obj is not None:
            value = _tb20f_var(obj, obj)
            if value is not None:
                return value
    return default


def _tb20f_render_logs(self: _Tb20fAny) -> None:
    events = _tb20f_collect_audit_events(self)
    category = _tb20f_get_filter(self, 'audit_category_var', 'audit_category_filter', default='All')
    severity = _tb20f_get_filter(self, 'audit_severity_var', 'audit_severity_filter', default='All')
    level = _tb20f_get_filter(self, 'audit_level_var', 'audit_level_filter', default=None)
    code_prefix = _tb20f_get_filter(self, 'audit_code_prefix_var', 'audit_code_prefix_filter', default=None)
    query = _tb20f_get_filter(self, 'audit_search_var', 'audit_query_var', 'audit_text_var', default=None)
    correlation = _tb20f_get_filter(self, 'audit_correlation_var', 'audit_correlation_filter', default=None)
    filtered = filter_audit_events(events, category=category, severity=severity, level=level, code_prefix=code_prefix, q=query, correlation=correlation)
    text = '\n'.join(format_log_line(item) for item in filtered)
    _tb20f_widget_text(self, _tb20f_get(self, 'audit_box', None) or _tb20f_get(self, 'audit_log_box', None) or _tb20f_get(self, 'logs_box', None), text)
    _tb20f_widget_text(self, _tb20f_get(self, 'audit_summary_box', None), build_audit_summary_text({'total': len(events)}, filtered))


def _tb20f_render_status(self: _Tb20fAny, status: dict[str, _Tb20fAny]) -> None:
    status = _tb20f_dict(status)
    health = _tb20f_dict(status.get('health_snapshot'))
    risk = _tb20f_dict(status.get('risk_snapshot') or status.get('session'))
    ai = _tb20f_dict(status.get('ai_snapshot'))
    pending = _tb20f_pending(status)
    position = _tb20f_position(status)
    balances = _tb20f_dict(status.get('balances'))
    symbol = str(status.get('symbol') or 'ETHUSDT')
    base_asset = symbol[:-4] if symbol.endswith('USDT') else symbol
    base_balance = _tb20f_dict(balances.get(base_asset))
    quote_balance = _tb20f_dict(balances.get('USDT'))
    account = _tb20f_health_label(health.get('account_consistency'))
    pos_h = _tb20f_health_label(health.get('position_consistency'))
    pend_h = _tb20f_health_label(health.get('pending_consistency'))
    cockpit = ''
    if 'build_operator_cockpit_text' in globals():
        try:
            cockpit = build_operator_cockpit_text(status) + '\n\n'
        except Exception:
            cockpit = ''
    status_text = cockpit + '\n'.join([
        f'Account         : {account}', f'Position health : {pos_h}', f'Pending health  : {pend_h}',
        f"Current signal  : {status.get('last_signal', '-')}", f"Signal reason   : {status.get('signal_reason', '-')}", f"Trend           : {status.get('trend', '-')}", '',
        build_position_management_text({'position_snapshot': position}),
    ])
    _tb20f_widget_text(self, _tb20f_get(self, 'status_box', None), status_text)
    _tb20f_widget_text(self, _tb20f_get(self, 'risk_box', None), '\n'.join([
        f"Daily PnL       : {_tb20f_fmt(risk.get('daily_realized_pnl'), 6)}", f"Daily trades    : {_tb20f_int(risk.get('daily_trade_count'))}",
        f"Consec losses   : {_tb20f_int(risk.get('consecutive_losses'))}", f"Safe mode       : {_tb20f_bool(risk.get('safe_mode'))}", f"Kill switch     : {_tb20f_bool(risk.get('kill_switch_active'))}",
    ]))
    _tb20f_widget_text(self, _tb20f_get(self, 'position_box', None), build_position_management_text({'position_snapshot': position}))
    conf = ai.get('confidence')
    conf_text = '-' if conf is None else f'%{_tb20f_float(conf) * 100:.1f}' if abs(_tb20f_float(conf)) <= 1 else f'%{_tb20f_float(conf):.1f}'
    _tb20f_widget_text(self, _tb20f_get(self, 'ai_box', None), '\n'.join([f"AI enabled      : {_tb20f_bool(ai.get('enabled'))}", f"Provider        : {ai.get('provider') or ai.get('mode') or '-'}", f"Model           : {ai.get('model_path', '-')}", f"Confidence      : {conf_text}", f"Trend           : {ai.get('trend', '-')}"]))
    _tb20f_widget_text(self, _tb20f_get(self, 'pending_box', None), '\n'.join([f"Pending order   : {'YES' if _tb20f_bool(pending.get('present')) else 'NO'}", f"Side            : {pending.get('side') or '-'}", f"Submitted qty   : {_tb20f_fmt(pending.get('submitted_qty') or pending.get('qty'), 8)}", f"Executed qty    : {_tb20f_fmt(pending.get('executed_qty'), 8)}", f"Remaining qty   : {_tb20f_fmt(pending.get('remaining_qty'), 8)}", f"Status          : {pending.get('status') or '-'}"]))
    _tb20f_widget_text(self, _tb20f_get(self, 'log_box', None), '\n'.join([f'Health          : {account}/{pos_h}/{pend_h}', f"Model           : {ai.get('model_path', '-')}", f"Base balance    : {_tb20f_fmt(base_balance.get('free'), 8)}", f"Quote balance   : {_tb20f_fmt(quote_balance.get('free'), 8)}"]))
    _tb20f_apply_health_aware_controls(self, status)


def _tb20f_render_event_timeline(self: _Tb20fAny) -> None:
    events = [dict(item) for item in _tb20f_list(_tb20f_get(self, '_log_items', [])) if isinstance(item, dict)]
    category = _tb20f_get(self, '_event_filter_value', 'All')
    filtered = filter_audit_events(events, category=category, order='asc') if not _tb20f_is_all(category) else filter_audit_events(events, order='asc')
    _tb20f_widget_text(self, _tb20f_get(self, 'event_box', None), '\n'.join(format_log_line(item) for item in filtered))
    label = _tb20f_get(self, 'event_count_label', None)
    _tb20f_cfg(label, text=(f'{category}: {len(filtered)} event' if not _tb20f_is_all(category) else f'All: {len(filtered)} event'))


def _tb20f_closed_trades(events: list[dict[str, _Tb20fAny]]) -> list[dict[str, _Tb20fAny]]:
    trades = []
    for item in events:
        if str(item.get('code') or '').upper() == 'POSITION_CLOSED':
            data = _tb20f_dict(item.get('data'))
            trades.append({'symbol': data.get('symbol') or item.get('symbol') or 'ETHUSDT', 'pnl': _tb20f_float(data.get('pnl', data.get('realized_pnl', item.get('pnl')))), 'ts': _tb20f_float(item.get('ts'))})
    return trades


def _tb20f_wlbe(trades: list[dict[str, _Tb20fAny]]) -> tuple[int, int, int]:
    w = l = b = 0
    for trade in trades:
        pnl = _tb20f_float(trade.get('pnl'))
        if pnl > 1e-9: w += 1
        elif pnl < -1e-9: l += 1
        else: b += 1
    return w, l, b


def _tb20f_trade_list(trades: list[dict[str, _Tb20fAny]]) -> str:
    return ' / '.join(f"{trade.get('symbol') or 'ETHUSDT'} {_tb20f_float(trade.get('pnl')):.6f}" for trade in trades) or '-'


def _tb20f_render_session_summary(self: _Tb20fAny, status: dict[str, _Tb20fAny] | None = None) -> None:
    status = _tb20f_dict(status)
    events = [dict(item) for item in _tb20f_list(_tb20f_get(self, '_log_items', [])) if isinstance(item, dict)]
    all_trades = _tb20f_closed_trades(events)
    reset_ts = None
    for item in events:
        if str(item.get('code') or '').upper() == 'RISK_STATS_RESET':
            reset_ts = _tb20f_float(item.get('ts'))
    if reset_ts is not None:
        scoped = [t for t in all_trades if _tb20f_float(t.get('ts')) > reset_ts]; prefix = 'Today'
    else:
        scoped = all_trades; prefix = 'Tracked'
    session = _tb20f_dict(status.get('session')); risk = _tb20f_dict(status.get('risk_snapshot')); ai = _tb20f_dict(status.get('ai_snapshot')); health = _tb20f_dict(status.get('health_snapshot'))
    daily_count = _tb20f_int(session.get('daily_trade_count', risk.get('daily_trade_count', len(scoped))))
    if reset_ts is not None and daily_count == len(scoped):
        prefix = 'Today'
    wins, losses, bes = _tb20f_wlbe(scoped)
    tracked_pnl = sum(_tb20f_float(t.get('pnl')) for t in scoped)
    warnings = [item for item in events if _tb20f_event_severity(item) in {'warning', 'error'}]
    last_warning = str(warnings[-1].get('code')) if warnings else '-'
    health_text = '/'.join(_tb20f_health_label(health.get(k)) for k in ('account_consistency', 'position_consistency', 'pending_consistency'))
    conf = ai.get('confidence'); conf_text = '-' if conf is None else f'%{_tb20f_float(conf) * 100:.1f}' if abs(_tb20f_float(conf)) <= 1 else f'%{_tb20f_float(conf):.1f}'
    scope_note = '-' if daily_count == len(scoped) else f'partial log scope ({len(scoped)}/{daily_count})'
    lines = [
        f"Current signal  : {status.get('last_signal', '-')}", f"Signal reason   : {status.get('signal_reason', '-')}", f"Trend           : {status.get('trend', '-')}",
        f"Tracked PnL     : {tracked_pnl:.6f}", f"Trades today    : {daily_count}", f"{prefix} W/L/BE  : {wins}/{losses}/{bes}", f"{prefix} trades  : {_tb20f_trade_list(scoped)}",
    ]
    if prefix == 'Today':
        lines.append(f"Recent hist.    : {_tb20f_trade_list(all_trades[-3:])}")
    lines.extend([f"Last warning    : {last_warning}", f"Health          : {health_text}", f"Model           : {ai.get('model_path', '-')}", f"Confidence      : {conf_text}", f"Scope note      : {scope_note}"])
    _tb20f_widget_text(self, _tb20f_get(self, 'log_box', None), '\n'.join(lines))


def _tb20f_poll_health_and_status(self: _Tb20fAny) -> None:
    try:
        health = self.api_get('/health', timeout=1.0)
    except Exception as exc:
        try: self._last_connected = False
        except Exception: pass
        _tb20f_set_offline_ui(self, str(exc)); return
    try: self._last_connected = bool(_tb20f_dict(health).get('ok'))
    except Exception: self._last_connected = True
    _tb20f_cfg(_tb20f_get(self, 'lbl_connection', None), text='Backend: ONLINE', text_color=('green', 'light green'))
    _tb20f_cfg(_tb20f_get(self, 'lbl_symbol', None), text=f"Sembol: {_tb20f_dict(health).get('symbol', '-')}")
    try:
        status = self.api_get('/status', timeout=2.0)
    except Exception as exc:
        _tb20f_widget_text(self, _tb20f_get(self, 'status_box', None), 'Backend online, status payload alınamadı.')
        append = _tb20f_get(self, '_append_backend', None)
        if callable(append):
            try: append(f'STATUS degrade: {exc}')
            except Exception: pass
        return
    try: self._last_status = status
    except Exception: pass
    _tb20f_render_status(self, status)


def _tb20f_set_offline_ui(self: _Tb20fAny, reason: str = '-') -> None:
    config_name = getattr(_tb20f_get(self, 'config_path', None), 'name', 'config.local.yaml')
    text = f'Backend offline.\nReason: {reason}\n\nConfig: {config_name}'
    for attr in ('status_box', 'log_box', 'ai_box', 'risk_box', 'position_box', 'pending_box'):
        _tb20f_widget_text(self, _tb20f_get(self, attr, None), text)
    _tb20f_cfg(_tb20f_get(self, 'lbl_connection', None), text='Backend: OFFLINE', text_color=('red', 'orange'))


try:
    DashboardApp._set_button_enabled = _tb20f_set_button_enabled  # type: ignore[name-defined,method-assign]
    DashboardApp._apply_health_aware_controls = _tb20f_apply_health_aware_controls  # type: ignore[name-defined,method-assign]
    DashboardApp._api_post = _tb20f_api_post  # type: ignore[name-defined,method-assign]
    DashboardApp._render_status = _tb20f_render_status  # type: ignore[name-defined,method-assign]
    DashboardApp._render_logs = _tb20f_render_logs  # type: ignore[name-defined,method-assign]
    DashboardApp._render_event_timeline = _tb20f_render_event_timeline  # type: ignore[name-defined,method-assign]
    DashboardApp._render_session_summary = _tb20f_render_session_summary  # type: ignore[name-defined,method-assign]
    DashboardApp._poll_health_and_status = _tb20f_poll_health_and_status  # type: ignore[name-defined,method-assign]
    DashboardApp._set_offline_ui = _tb20f_set_offline_ui  # type: ignore[name-defined,method-assign]
except Exception:
    pass

# END 4B.4.3.6.6.20F DASHBOARD ROOT CONTRACT RESTORE
'''


def patch_text(text: str) -> str:
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        return before + '\n\n' + COMPAT_BLOCK.strip() + '\n\n' + after
    return text.rstrip() + '\n\n' + COMPAT_BLOCK.strip() + '\n'


def main() -> int:
    dashboard = Path.cwd() / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
    if not dashboard.exists():
        raise RuntimeError(f'dashboard.py not found: {dashboard}')
    updated = patch_text(dashboard.read_text(encoding='utf-8'))
    dashboard.write_text(updated, encoding='utf-8')
    checks = {
        'buttons_boolean_contract': "'buttons': buttons" in updated and "'force_buy': buttons['force_buy']" in updated,
        'effective_sl_and_ready_text': 'Effective SL    :' in updated and 'Protective exit :' in updated,
        'set_text_uses_dashboard_setter': "setter = _tb20f_get(app, '_set_text', None)" in updated,
        'button_style_contract': "'#8C8C8C', '#5F5F5F'" in updated and "'#3B8ED0', '#1F6AA5'" in updated,
        'audit_warning_summary': 'Warnings/errors :' in updated,
        'offline_english_contract': 'Backend offline.' in updated,
        'status_degrade_contract': 'Backend online, status payload alınamadı.' in updated,
        'class_methods_patched': 'DashboardApp._render_status = _tb20f_render_status' in updated,
    }
    print('4B.4.3.6.6.20f dashboard root contract restore patch applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(checks.values()):
        raise RuntimeError(f'20f verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
