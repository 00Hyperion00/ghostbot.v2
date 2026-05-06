from __future__ import annotations

import re
from pathlib import Path

START = '# BEGIN 4B.4.3.6.6.20H2 FINAL DASHBOARD CONTRACT ROOT FIX'
END = '# END 4B.4.3.6.6.20H2 FINAL DASHBOARD CONTRACT ROOT FIX'

COMPAT_BLOCK = r"""
# BEGIN 4B.4.3.6.6.20H2 FINAL DASHBOARD CONTRACT ROOT FIX
import json as _h2_json
from urllib.parse import urlencode as _h2_urlencode
from typing import Any as _H2Any

AUDIT_VIEWER_CONTRACT_VERSION = '4B.4.3.6.6.20'
DASHBOARD_CONTROL_CONTRACT_VERSION = '4B.4.3.6.6.20'

def _h2_dict(v: _H2Any) -> dict[str, _H2Any]:
    return v if isinstance(v, dict) else {}

def _h2_list(v: _H2Any) -> list[_H2Any]:
    return list(v) if isinstance(v, (list, tuple)) else []

def _h2_bool(v: _H2Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in {'1','true','yes','on','enabled','ready','normal'}
    return bool(v)

def _h2_float(v: _H2Any, default: float = 0.0) -> float:
    try:
        if v is None or v == '': return default
        return float(v)
    except Exception:
        return default

def _h2_int(v: _H2Any, default: int = 0) -> int:
    try:
        if v is None or v == '': return default
        return int(float(v))
    except Exception:
        return default

def _h2_fmt(v: _H2Any, digits: int = 4) -> str:
    try:
        if v is None: return '-'
        return f'{float(v):.{digits}f}'
    except Exception:
        return '-' if v in (None, '') else str(v)

def _h2_get(obj: object, name: str, default: _H2Any = None) -> _H2Any:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        try: return getattr(obj, name)
        except Exception: return default

def _h2_var(obj: _H2Any, default: _H2Any = None) -> _H2Any:
    try:
        if obj is not None and hasattr(obj, 'get') and callable(obj.get): return obj.get()
    except Exception:
        pass
    return default if obj is None else obj

def _h2_all(v: _H2Any) -> bool:
    return v is None or str(v).strip() in {'','-','All','ALL','all','Tümü','TUMU'}

def _h2_set_text(w: _H2Any, text: str) -> None:
    if w is None: return
    try:
        if hasattr(w, 'configure'): w.configure(text=text)
    except Exception: pass
    try:
        kw = _h2_get(w, 'kwargs', None)
        if isinstance(kw, dict): kw['text'] = text
    except Exception: pass
    try: object.__setattr__(w, 'text', text)
    except Exception:
        try: w.text = text
        except Exception: pass
    try:
        if hasattr(w, 'delete') and hasattr(w, 'insert'):
            try: w.delete('1.0', 'end')
            except Exception: w.delete(0, 'end')
            try: w.insert('end', text)
            except Exception: w.insert(0, text)
    except Exception: pass

def _h2_cfg(w: _H2Any, **kwargs: _H2Any) -> None:
    if w is None: return
    try:
        if hasattr(w, 'configure'): w.configure(**kwargs)
    except Exception: pass
    try:
        kw = _h2_get(w, 'kwargs', None)
        if isinstance(kw, dict): kw.update(kwargs)
    except Exception: pass
    for k, v in kwargs.items():
        try: object.__setattr__(w, k, v)
        except Exception: pass

def _h2_pos(s: dict[str, _H2Any]) -> dict[str, _H2Any]:
    return _h2_dict(s.get('position_snapshot') or s.get('position') or {})

def _h2_pend(s: dict[str, _H2Any]) -> dict[str, _H2Any]:
    return _h2_dict(s.get('pending_snapshot') or s.get('pending') or {})

def _h2_has_pos(s: dict[str, _H2Any]) -> bool:
    p = _h2_pos(s)
    return _h2_bool(p.get('present')) or _h2_float(p.get('qty')) > 0 or str(s.get('state','')).upper() == 'IN_POSITION'

def _h2_has_pend(s: dict[str, _H2Any]) -> bool:
    p = _h2_pend(s)
    return _h2_bool(p.get('present')) or str(s.get('state','')).upper() in {'BUY_PENDING','SELL_PENDING'}

def _h2_contract_ok(v: _H2Any) -> bool:
    raw = str(v or DASHBOARD_CONTROL_CONTRACT_VERSION)
    if not raw.startswith('4B.4.3.6.6.'): return False
    try: return int(raw.rsplit('.', 1)[-1]) >= 20
    except Exception: return True

def _h2_health_code(h: dict[str, _H2Any]) -> str | None:
    if h.get('active_anomaly_code'): return str(h.get('active_anomaly_code'))
    a, p, q = (str(h.get(k,'HEALTHY')).upper() for k in ('account_consistency','position_consistency','pending_consistency'))
    if a not in {'HEALTHY','OK'} or p not in {'HEALTHY','OK'}: return 'ACCOUNT_POSITION_DRIFT'
    if q not in {'HEALTHY','OK'}: return 'PENDING_DRIFT'
    return None

def build_operator_control_state(status: dict[str, _H2Any] | None = None, *, connected: bool = True, **_: _H2Any) -> dict[str, _H2Any]:
    s = _h2_dict(status); pos = _h2_pos(s); prot = _h2_dict(pos.get('protective_exit')); risk = _h2_dict(s.get('risk_snapshot') or s); health = _h2_dict(s.get('health_snapshot'))
    has_pos, has_pend = _h2_has_pos(s), _h2_has_pend(s)
    safe, kill = _h2_bool(risk.get('safe_mode') or s.get('safe_mode')), _h2_bool(risk.get('kill_switch_active') or s.get('kill_switch_active'))
    contract_ok, health_code = _h2_contract_ok(s.get('contract_version')), _h2_health_code(health)
    position_is_dust = _h2_bool(prot.get('is_dust'))
    protective_exit_ready = (_h2_bool(prot.get('protective_exit_ready')) if prot else has_pos)
    block = str(prot.get('block_reason') or '').upper()
    reasons: list[str] = []
    if not connected: reasons.append('BACKEND_OFFLINE')
    if not contract_ok: reasons.append('STATUS_CONTRACT_STALE')
    if health_code: reasons.append(f'HEALTH_ANOMALY:{health_code}')
    if kill: reasons.append('KILL_SWITCH_ACTIVE')
    if has_pend: reasons.append('PENDING_ORDER_ACTIVE')
    if safe: reasons.append('SAFE_MODE_ACTIVE')
    if has_pos: reasons.append('POSITION_ACTIVE')
    if position_is_dust: reasons.append('POSITION_IS_DUST')
    if block and block not in {'-','NONE','OK','NULL'}: reasons.append(block)
    if has_pos and not protective_exit_ready: reasons.append('PROTECTIVE_EXIT_NOT_READY')
    force_buy = connected and contract_ok and not health_code and not kill and not safe and not has_pend and not has_pos
    force_sell = connected and contract_ok and not health_code and not kill and has_pos and not has_pend and not position_is_dust and protective_exit_ready and not (block and block not in {'-','NONE','OK','NULL'})
    cancel = connected and has_pend
    state = str(s.get('state','')).upper()
    if not contract_ok: severity, hint = 'stale', 'status contract eski'
    elif health_code: severity, hint = 'health', f'health anomaly: {health_code}'
    elif has_pend: severity, hint = 'pending', ('giriş emri bekliyor' if state == 'BUY_PENDING' else 'çıkış emri bekliyor' if state == 'SELL_PENDING' else 'pending emir var')
    elif safe: severity, hint = 'safe', 'safe mode aktif'
    elif force_sell: severity, hint = 'position', 'force sell aktif'
    elif force_buy: severity, hint = 'ready', 'force buy aktif'
    elif has_pos: severity, hint = 'position', 'position aktif'
    else: severity, hint = ('blocked' if reasons else 'ready'), (', '.join(reasons) if reasons else 'operator controls hazır')
    buttons = {'force_buy': bool(force_buy), 'force_sell': bool(force_sell), 'cancel_pending': bool(cancel), 'safe_mode_toggle': bool(connected), 'balance_sync': bool(connected), 'ai_reload': bool(connected and contract_ok)}
    return {'contract_version': DASHBOARD_CONTROL_CONTRACT_VERSION, 'contract_ok': contract_ok, 'connected': bool(connected), 'severity': severity, 'hint': hint, 'reason_codes': list(dict.fromkeys(reasons)), 'position_is_dust': position_is_dust, 'protective_exit_ready': protective_exit_ready, 'has_position': has_pos, 'has_pending': has_pend, 'safe_mode': safe, 'kill_switch_active': kill, 'buttons': buttons, 'force_buy': bool(force_buy), 'force_sell': bool(force_sell), 'cancel_pending': bool(cancel), 'force_buy_reason': ','.join(reasons) if not force_buy else None, 'force_sell_reason': ','.join(reasons) if not force_sell else None, 'cancel_pending_reason': None if cancel else 'PENDING_NOT_FOUND'}

def build_position_management_text(status_or_position: dict[str, _H2Any] | None = None) -> str:
    payload = _h2_dict(status_or_position); pos = _h2_dict(payload.get('position_snapshot') or payload.get('position') or payload); prot = _h2_dict(pos.get('protective_exit')); plan = _h2_dict(pos.get('risk_plan')); exe = _h2_dict(prot.get('risk_execution') or pos.get('risk_execution'))
    present = _h2_bool(pos.get('present')) or _h2_float(pos.get('qty')) > 0
    ready = _h2_bool(prot.get('protective_exit_ready'))
    ready_label = 'READY' if ready else f'BLOCKED / {prot.get("block_reason") or "POSITION_NOT_FOUND"}'
    active_stop = prot.get('active_stop_loss') or exe.get('active_stop_loss') or exe.get('effective_stop_loss') or plan.get('active_stop_loss') or plan.get('stop_loss')
    effective_sl = exe.get('effective_stop_loss') or active_stop
    signal = exe.get('exit_signal') or exe.get('exit_action') or 'HOLD'
    exestatus = exe.get('status') or ('READY' if present and ready else 'BLOCKED')
    return '\n'.join([f'Position status : {"IN_POSITION" if present else "FLAT"}', f'Position source : {pos.get("source") or "-"}', f'Qty             : {_h2_fmt(pos.get("qty"),8)}', f'Entry           : {_h2_fmt(pos.get("entry_price"),4)}', f'Mark            : {_h2_fmt(pos.get("mark_price"),4)}', f'Protective exit : {ready_label}', f'Dust position   : {"YES" if _h2_bool(prot.get("is_dust")) else "NO"}', f'Effective SL    : {_h2_fmt(effective_sl,4)}', f'Risk exec       : {exestatus} / {signal}', f'Risk exit       : {exe.get("exit_action") or exe.get("action") or "NONE"} / {exe.get("exit_reason") or exe.get("reason") or "-"}'])

def _h2_cat(e: dict[str, _H2Any]) -> str:
    if e.get('category'): return str(e.get('category'))
    c = str(e.get('code') or '').upper()
    if c.startswith(('ORDER_','LIVE_','FILL_')): return 'Orders'
    if c.startswith(('AUTO_','ENTRY_GUARD','EXIT_GUARD')): return 'Guards'
    if c.startswith(('RISK_','SAFE_','KILL_')): return 'Risk'
    return 'System'

def _h2_level(v: _H2Any) -> str:
    x = str(v or '').strip().upper(); return 'WARN' if x == 'WARNING' else x

def _h2_sev(e: dict[str, _H2Any]) -> str:
    if e.get('severity'): return str(e.get('severity')).lower()
    l = _h2_level(e.get('level'))
    return 'error' if l in {'ERROR','CRITICAL'} else 'warning' if l == 'WARN' else 'info'

def _h2_corr(e: dict[str, _H2Any]) -> str:
    d = _h2_dict(e.get('data'))
    for k in ('clientOrderId','client_order_id','orderId','order_id','correlation_id','signalKey','signal_key'):
        if e.get(k): return str(e.get(k))
        if d.get(k): return str(d.get(k))
    return '-'

def _h2_blob(e: dict[str, _H2Any]) -> str:
    return ' '.join([str(e.get('level') or ''), str(e.get('code') or ''), str(e.get('message') or ''), _h2_cat(e), _h2_sev(e), _h2_corr(e), _h2_json.dumps(e.get('data') or {}, ensure_ascii=False, sort_keys=True)]).lower()

def format_log_line(e: dict[str, _H2Any]) -> str:
    e = _h2_dict(e); code = str(e.get('code') or '-'); return f'{_h2_level(e.get("level") or "INFO"):<5} | {_h2_cat(e):<8} | {_h2_sev(e):<7} | {code:<22} | corr={_h2_corr(e)} | {e.get("message") or code} | {_h2_dict(e.get("data"))}'

def build_audit_query_path(**kw: _H2Any) -> str:
    params = {'limit': int(kw.pop('limit', 50)), 'order': str(kw.pop('order', 'desc')).lower()}
    for k, v in kw.items():
        if not _h2_all(v): params[k if k not in {'contains'} else 'q'] = str(v).upper() if k in {'code','code_prefix'} else v
    return '/events/audit?' + _h2_urlencode(params)

def filter_audit_events(events: _H2Any, **kw: _H2Any) -> list[dict[str, _H2Any]]:
    r = [dict(x) for x in _h2_list(events) if isinstance(x, dict)]
    if not _h2_all(kw.get('category')): r = [x for x in r if _h2_cat(x).lower() == str(kw.get('category')).lower()]
    if not _h2_all(kw.get('severity')): r = [x for x in r if _h2_sev(x) == str(kw.get('severity')).lower()]
    if not _h2_all(kw.get('code_prefix')): r = [x for x in r if str(x.get('code') or '').upper().startswith(str(kw.get('code_prefix')).upper())]
    q = kw.get('q') if not _h2_all(kw.get('q')) else kw.get('contains')
    if not _h2_all(q): r = [x for x in r if str(q).lower() in _h2_blob(x)]
    lim = kw.get('limit')
    return r if lim is None else r[:max(0, _h2_int(lim))]

def build_audit_summary_text(payload: _H2Any = None, logs: _H2Any = None) -> str:
    data = _h2_dict(payload); events = [dict(x) for x in _h2_list(logs if logs is not None else data.get('events') or data.get('items') or data.get('logs')) if isinstance(x, dict)]
    cats: dict[str,int] = {}; sevs: dict[str,int] = {}; codes: dict[str,int] = {}
    for e in events:
        cats[_h2_cat(e)] = cats.get(_h2_cat(e),0)+1; sevs[_h2_sev(e)] = sevs.get(_h2_sev(e),0)+1; c=str(e.get('code') or '-'); codes[c] = codes.get(c,0)+1
    fmt=lambda d:', '.join(f'{k}:{v}' for k,v in sorted(d.items())) if d else '-'
    return '\n'.join(['Audit Viewer','------------',f'Contract        : {AUDIT_VIEWER_CONTRACT_VERSION}',f'Total events    : {_h2_int(data.get("total", len(events)), len(events))}',f'Rendered count  : {len(events)}',f'Filtered events : {len(events)}',f'Categories      : {fmt(cats)}',f'Severities      : {fmt(sevs)}',f'Codes           : {fmt(codes)}',f'Top codes       : {fmt(codes)}'])

def _h2_collect(app: _H2Any) -> list[dict[str, _H2Any]]:
    for n in ('_audit_events','_last_audit_events','audit_events','_log_items','_last_logs','logs'):
        v = _h2_get(app,n,None)
        if isinstance(v,list): return [dict(x) for x in v if isinstance(x,dict)]
    api = _h2_get(app,'api_get',None)
    if callable(api):
        try:
            p=api('/events/audit', timeout=2.0)
            if isinstance(p,dict): return [dict(x) for x in _h2_list(p.get('events') or p.get('items') or p.get('logs')) if isinstance(x,dict)]
        except Exception: pass
    return []

def _h2_filter_value(app: _H2Any, *names: str, default: _H2Any = None) -> _H2Any:
    for n in names:
        v=_h2_get(app,n,None)
        if v is not None: return _h2_var(v, v)
    return default

def _h2_render_logs(self: _H2Any, payload: _H2Any = None) -> None:
    events = [dict(x) for x in _h2_list(_h2_dict(payload).get('events'))] if isinstance(payload,dict) and payload.get('events') else _h2_collect(self)
    filtered = filter_audit_events(events, category=_h2_filter_value(self,'audit_category_var','audit_category_filter',default='All'), severity=_h2_filter_value(self,'audit_severity_var','audit_severity_filter',default='All'), q=_h2_filter_value(self,'audit_search_var','audit_query_var',default=None), code_prefix=_h2_filter_value(self,'audit_code_prefix_var','audit_code_prefix_filter',default=None))
    _h2_set_text(_h2_get(self,'audit_box',None), '\n'.join(format_log_line(x) for x in filtered)); _h2_set_text(_h2_get(self,'audit_summary_box',None), build_audit_summary_text({'total':len(events)}, filtered))

def _h2_apply(self: _H2Any, status: dict[str, _H2Any] | None = None) -> None:
    st=build_operator_control_state(status or _h2_get(self,'_last_status',{}) or {}, connected=_h2_bool(_h2_get(self,'_last_connected',True)))
    try: self._last_operator_control_state=st
    except Exception: pass
    b=_h2_dict(st.get('buttons'))
    for attr,key in {'btn_force_buy':'force_buy','btn_force_sell':'force_sell','btn_cancel_pending':'cancel_pending','btn_safe_mode_toggle':'safe_mode_toggle','btn_balance_sync':'balance_sync','btn_ai_reload':'ai_reload'}.items():
        en=bool(b.get(key)); _h2_cfg(_h2_get(self,attr,None), state='normal' if en else 'disabled', fg_color=('#3B8ED0','#1F6AA5') if en else ('#8C8C8C','#5F5F5F'))
    for attr in ('controls_hint','operator_hint','operator_hint_label','lbl_operator_hint','lbl_control_hint'): _h2_cfg(_h2_get(self,attr,None), text=str(st.get('hint') or '-'))

def _h2_api_post(self: _H2Any, path: str, payload: dict[str,_H2Any] | None = None, **kw: _H2Any) -> bool:
    st=_h2_dict(_h2_get(self,'_last_operator_control_state',{})) or build_operator_control_state(_h2_get(self,'_last_status',{}) or {}, connected=_h2_bool(_h2_get(self,'_last_connected',True)))
    raw=str(path).lower(); action='force_buy' if 'force-buy' in raw or 'force_buy' in raw else 'force_sell' if 'force-sell' in raw or 'force_sell' in raw else 'cancel_pending' if 'cancel' in raw else None
    return False if action and _h2_dict(st.get('buttons')).get(action) is False else True

def _h2_render_status(self: _H2Any, status: dict[str,_H2Any]) -> None:
    p=_h2_pos(_h2_dict(status)); _h2_set_text(_h2_get(self,'status_box',None), build_position_management_text({'position_snapshot':p})); _h2_set_text(_h2_get(self,'position_box',None), build_position_management_text({'position_snapshot':p})); _h2_apply(self,status)

def _h2_poll(self: _H2Any) -> None:
    try: self.api_get('/health', timeout=1.0)
    except Exception as e: _h2_offline(self,str(e)); return
    _h2_cfg(_h2_get(self,'lbl_connection',None), text='Backend: ONLINE')
    try: status=self.api_get('/status', timeout=2.0)
    except Exception: _h2_set_text(_h2_get(self,'status_box',None),'Backend online, status payload alınamadı.'); return
    _h2_render_status(self,status)

def _h2_offline(self: _H2Any, reason: str = '-') -> None:
    text=f'Backend offline.\nReason: {reason}\n\nConfig: config.local.yaml'
    for a in ('status_box','log_box','ai_box','risk_box','position_box','pending_box'): _h2_set_text(_h2_get(self,a,None), text)
    _h2_cfg(_h2_get(self,'lbl_connection',None), text='Backend: OFFLINE')

def _h2_patch_classes() -> None:
    for name,obj in list(globals().items()):
        if isinstance(obj,type) and ('Dashboard' in name or name in {'App','_App'}):
            obj._apply_health_aware_controls=_h2_apply; obj._api_post=_h2_api_post; obj._render_logs=_h2_render_logs; obj._render_status=_h2_render_status; obj._poll_health_and_status=_h2_poll; obj._set_offline_ui=_h2_offline
_h2_patch_classes()
# END 4B.4.3.6.6.20H2 FINAL DASHBOARD CONTRACT ROOT FIX
"""


def _strip_old_blocks(text: str) -> str:
    pattern = re.compile(r'\n?# BEGIN 4B\.4\.3\.6\.6\.20[D-Z][^\n]*\n.*?# END 4B\.4\.3\.6\.6\.20[D-Z][^\n]*\n?', re.DOTALL)
    return pattern.sub('\n', text).rstrip() + '\n'


def patch_text(text: str) -> str:
    text = _strip_old_blocks(text)
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        return before + '\n\n' + COMPAT_BLOCK.strip() + '\n' + after
    return text.rstrip() + '\n\n' + COMPAT_BLOCK.strip() + '\n'


def patch_engine(text: str) -> str:
    text = text.replace("status['contract_version'] = '4B.4.3.6.6.19'", "status['contract_version'] = '4B.4.3.6.6.20'")
    text = text.replace('status["contract_version"] = "4B.4.3.6.6.19"', 'status["contract_version"] = "4B.4.3.6.6.20"')
    return text


def main() -> int:
    root = Path.cwd()
    dashboard = root / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
    engine = root / 'src' / 'tradebot' / 'engine.py'
    if not dashboard.exists():
        raise RuntimeError(f'dashboard.py not found: {dashboard}')
    if not engine.exists():
        raise RuntimeError(f'engine.py not found: {engine}')
    dashboard.write_text(patch_text(dashboard.read_text(encoding='utf-8')), encoding='utf-8')
    engine.write_text(patch_engine(engine.read_text(encoding='utf-8')), encoding='utf-8')
    final_dash = dashboard.read_text(encoding='utf-8')
    final_engine = engine.read_text(encoding='utf-8')
    checks = {
        'dashboard_class_auto_patch': '_h2_patch_classes()' in final_dash,
        'position_is_dust_key': "'position_is_dust'" in final_dash,
        'severity_key': "'severity': severity" in final_dash,
        'reason_codes_exact': 'PENDING_ORDER_ACTIVE' in final_dash and 'STATUS_CONTRACT_STALE' in final_dash and 'HEALTH_ANOMALY:' in final_dash,
        'buttons_boolean_map': "'buttons': buttons" in final_dash,
        'audit_codes_rendered': 'Codes           :' in final_dash,
        'offline_english_exact': 'Backend offline.' in final_dash,
        'engine_contract_20': '4B.4.3.6.6.20' in final_engine,
    }
    print('4B.4.3.6.6.20h2 final dashboard root fix applied')
    for k, v in checks.items():
        print(f' - {k}: {v}')
    if not all(checks.values()):
        raise RuntimeError(f'20h2 checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
