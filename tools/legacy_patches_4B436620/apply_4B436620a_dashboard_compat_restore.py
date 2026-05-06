from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'

COMPAT_MARKER = '# 4B.4.3.6.6.20a dashboard compatibility helpers'

COMPAT_BLOCK = r'''
# 4B.4.3.6.6.20a dashboard compatibility helpers
AUDIT_VIEWER_CONTRACT_VERSION = '4B.4.3.6.6.20'
DASHBOARD_CONTROL_CONTRACT_VERSION = '4B.4.3.6.6.20'


def _fmt_float(value: Any, digits: int = 4) -> str:
    try:
        if value is None:
            return '-'
        return f'{float(value):.{int(digits)}f}'
    except Exception:
        return str(value)


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return '-'
        numeric = float(value)
        if abs(numeric) <= 1.0:
            numeric *= 100.0
        return f'{numeric:.2f}%'
    except Exception:
        return str(value)


def _as_snapshot_position(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    if 'position_snapshot' in payload:
        return payload.get('position_snapshot') or {}
    return payload


def build_position_management_text(status_or_position: dict[str, Any] | None) -> str:
    position = _as_snapshot_position(status_or_position)
    protective = position.get('protective_exit') or {}
    risk_plan = position.get('risk_plan') or {}
    risk_exec = protective.get('risk_execution') or position.get('risk_execution') or {}

    if not position.get('present'):
        block_reason = protective.get('block_reason') or 'POSITION_NOT_FOUND'
        return '\n'.join([
            'Position status : FLAT',
            f'Position source : {position.get("source") or "-"}',
            f'Qty             : {_fmt_float(position.get("qty"), 8)}',
            f'Mark            : {_fmt_float(position.get("mark_price"), 4)}',
            f'Protective exit : BLOCKED / {block_reason}',
            f'Exit qty        : {_fmt_float(protective.get("tradable_exit_qty"), 8)}',
            f'Exit notional   : {_fmt_float(protective.get("exit_notional"), 4)}',
            f'Dust position   : {bool(protective.get("is_dust", False))}',
            'Risk plan       : MISSING',
        ])

    ready_label = 'READY' if protective.get('protective_exit_ready') else f'BLOCKED / {protective.get("block_reason") or "-"}'
    dust_label = 'YES' if protective.get('is_dust') else 'NO'
    active_stop = protective.get('active_stop_loss') or risk_exec.get('active_stop_loss') or risk_plan.get('stop_loss')
    partial_done = protective.get('partial_tp_triggered') or risk_exec.get('partial_tp_triggered') or risk_exec.get('partial_tp_done')
    return '\n'.join([
        'Position status : IN_POSITION',
        f'Position source : {position.get("source") or "-"}',
        f'Qty             : {_fmt_float(position.get("qty"), 8)}',
        f'Entry           : {_fmt_float(position.get("entry_price"), 4)}',
        f'Mark            : {_fmt_float(position.get("mark_price"), 4)}',
        f'Unrealized PnL  : {_fmt_float(position.get("unrealized_pnl"), 6)} ({_fmt_pct(position.get("unrealized_pnl_pct"))})',
        f'Protective exit : {ready_label}',
        f'Exit qty        : {_fmt_float(protective.get("tradable_exit_qty"), 8)}',
        f'Exit notional   : {_fmt_float(protective.get("exit_notional"), 4)}',
        f'Dust position   : {dust_label}',
        f'Risk plan       : {"READY" if risk_plan else "MISSING"}',
        f'Stop loss       : {_fmt_float(protective.get("stop_loss") or risk_plan.get("stop_loss"), 4)}',
        f'Effective SL    : {_fmt_float(risk_exec.get("effective_stop_loss") or active_stop, 4)}',
        f'Active stop     : {_fmt_float(active_stop, 4)}',
        f'Take profit     : {_fmt_float(protective.get("take_profit") or risk_plan.get("take_profit"), 4)}',
        f'Dist. to SL     : {_fmt_float(protective.get("distance_to_stop"), 4)} ({_fmt_pct(protective.get("distance_to_stop_pct"))})',
        f'Dist. to TP     : {_fmt_float(protective.get("distance_to_take_profit"), 4)} ({_fmt_pct(protective.get("distance_to_take_profit_pct"))})',
        f'Break-even      : {bool(protective.get("break_even_armed") or risk_exec.get("break_even_armed"))} / trg {_fmt_float(protective.get("break_even_trigger_price") or risk_plan.get("break_even_trigger_price"), 4)}',
        f'Trailing        : {bool(protective.get("trailing_enabled") or risk_plan.get("trailing_enabled"))} / armed {bool(protective.get("trailing_armed") or risk_exec.get("trailing_armed"))} / stop {_fmt_float(protective.get("trailing_stop") or risk_exec.get("trailing_stop"), 4)}',
        f'Partial TP      : {_fmt_float(protective.get("partial_tp_price") or risk_plan.get("partial_tp_price"), 4)} / {_fmt_pct(protective.get("partial_tp_close_pct") or risk_plan.get("partial_tp_close_pct"))} / hit {bool(partial_done)}',
        f'Partial TP done : {bool(partial_done)}',
        f'Risk exit       : {risk_exec.get("exit_action") or "NONE"} / {risk_exec.get("exit_reason") or protective.get("last_exit_reason") or "-"}',
    ])


def _button_state(enabled: bool, reason: str = '') -> dict[str, Any]:
    return {'enabled': bool(enabled), 'reason': reason or None}


def build_operator_control_state(status: dict[str, Any] | None) -> dict[str, Any]:
    status = status or {}
    position = status.get('position_snapshot') or {}
    pending = status.get('pending_snapshot') or {}
    risk = status.get('risk_snapshot') or {}
    config = status.get('config_safety_snapshot') or {}

    running = bool(status.get('running', status.get('engine_running', False)))
    has_position = bool(position.get('present') or status.get('has_position', False))
    has_pending = bool(pending.get('present') or status.get('has_pending', False))
    safe_mode = bool(risk.get('safe_mode', False))
    kill_switch = bool(risk.get('kill_switch_active', False))
    config_safe = bool(config.get('safe_to_trade', True))
    config_auto_safe = bool(config.get('safe_to_auto_trade', config_safe))

    block_reasons: list[str] = []
    if not running:
        block_reasons.append('ENGINE_NOT_RUNNING')
    if has_pending:
        block_reasons.append('PENDING_ORDER_EXISTS')
    if has_position:
        block_reasons.append('POSITION_EXISTS')
    if safe_mode:
        block_reasons.append('SAFE_MODE_ACTIVE')
    if kill_switch:
        block_reasons.append('KILL_SWITCH_ACTIVE')
    if not config_safe:
        block_reasons.append('CONFIG_NOT_SAFE')

    force_buy_enabled = running and not has_pending and not has_position and not safe_mode and not kill_switch and config_safe
    force_sell_enabled = running and has_position and not has_pending and not kill_switch and config_safe
    cancel_pending_enabled = running and has_pending
    start_enabled = not running
    stop_enabled = running
    safe_mode_toggle_enabled = running
    balance_sync_enabled = running
    ai_reload_enabled = running

    controls = {
        'start_enabled': start_enabled,
        'stop_enabled': stop_enabled,
        'force_buy_enabled': force_buy_enabled,
        'force_sell_enabled': force_sell_enabled,
        'cancel_pending_enabled': cancel_pending_enabled,
        'safe_mode_toggle_enabled': safe_mode_toggle_enabled,
        'balance_sync_enabled': balance_sync_enabled,
        'ai_reload_enabled': ai_reload_enabled,
        'auto_trade_safe': config_auto_safe and not safe_mode and not kill_switch,
        'has_position': has_position,
        'has_pending': has_pending,
        'safe_mode': safe_mode,
        'kill_switch_active': kill_switch,
        'block_reasons': block_reasons,
        'buttons': {
            'start': _button_state(start_enabled, 'ENGINE_RUNNING' if running else ''),
            'stop': _button_state(stop_enabled, 'ENGINE_STOPPED' if not running else ''),
            'force_buy': _button_state(force_buy_enabled, ','.join(block_reasons)),
            'force_sell': _button_state(force_sell_enabled, 'POSITION_NOT_FOUND' if not has_position else ','.join(r for r in block_reasons if r != 'POSITION_EXISTS')),
            'cancel_pending': _button_state(cancel_pending_enabled, 'PENDING_NOT_FOUND' if not has_pending else ''),
            'safe_mode_toggle': _button_state(safe_mode_toggle_enabled, 'ENGINE_STOPPED' if not running else ''),
            'balance_sync': _button_state(balance_sync_enabled, 'ENGINE_STOPPED' if not running else ''),
            'ai_reload': _button_state(ai_reload_enabled, 'ENGINE_STOPPED' if not running else ''),
        },
    }
    controls.update(controls['buttons'])
    return controls


def build_audit_summary_text(payload: dict[str, Any] | None, logs: list[dict[str, Any]] | None = None) -> str:
    payload = payload or {}
    logs = logs or payload.get('events') or []
    codes: dict[str, int] = {}
    levels: dict[str, int] = {}
    for item in logs:
        code = str(item.get('code') or '-')
        level = str(item.get('level') or 'INFO')
        codes[code] = codes.get(code, 0) + 1
        levels[level] = levels.get(level, 0) + 1
    top_codes = ', '.join(f'{k}:{v}' for k, v in sorted(codes.items(), key=lambda kv: (-kv[1], kv[0]))[:5]) or '-'
    return '\n'.join([
        'Audit Viewer',
        '------------',
        f'Contract       : {AUDIT_VIEWER_CONTRACT_VERSION}',
        f'Total events   : {payload.get("total", payload.get("total_events", len(logs)))}',
        f'Filtered events: {len(logs)}',
        f'Levels         : {levels or {}}',
        f'Top codes      : {top_codes}',
    ])
'''

NEW_EXTRACT_METHOD = r'''    def _extract_training_output_path(self, line: str) -> str | None:
        import ast
        import json

        raw = str(line or '').strip()
        if not raw:
            return None

        payload: Any
        try:
            payload = json.loads(raw)
        except Exception:
            try:
                payload = ast.literal_eval(raw)
            except Exception:
                payload = None

        if isinstance(payload, dict):
            for key in ('model_path', 'output', 'output_path', 'model', 'path'):
                value = payload.get(key)
                if value:
                    return str(value)

        for marker in ('model_path=', 'output=', 'output_path='):
            if marker in raw:
                tail = raw.split(marker, 1)[1].strip().strip('"\'')
                return tail.split()[0].strip(',;') if tail else None
        return None
'''


def insert_compat_block(text: str) -> tuple[str, bool]:
    if COMPAT_MARKER in text:
        return text, False
    anchor = '\ndef safe_obj_getattr('
    if anchor not in text:
        raise RuntimeError('safe_obj_getattr anchor not found in dashboard.py')
    return text.replace(anchor, '\n' + COMPAT_BLOCK + '\n' + anchor, 1), True


def replace_extract_method(text: str) -> tuple[str, bool]:
    pattern = re.compile(
        r"    def _extract_training_output_path\(self, line: str\) -> str \| None:\n"
        r".*?"
        r"(?=    def _resolve_training_output_path\()",
        re.DOTALL,
    )
    new_text, count = pattern.subn(NEW_EXTRACT_METHOD + '\n', text, count=1)
    if count != 1:
        raise RuntimeError('Could not replace _extract_training_output_path method')
    return new_text, True

def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'{DASHBOARD} not found')
    text = DASHBOARD.read_text(encoding='utf-8')
    text, inserted = insert_compat_block(text)
    text, replaced_extract = replace_extract_method(text)
    DASHBOARD.write_text(text, encoding='utf-8')

    final = DASHBOARD.read_text(encoding='utf-8')
    checks = {
        'compat_block_present': COMPAT_MARKER in final,
        'build_position_management_text_present': 'def build_position_management_text' in final,
        'build_operator_control_state_present': 'def build_operator_control_state' in final,
        'audit_viewer_constant_present': 'AUDIT_VIEWER_CONTRACT_VERSION' in final,
        'json_loads_parser_present': 'json.loads(raw)' in final,
        'model_path_key_present': "'model_path'" in final,
    }
    if not all(checks.values()):
        raise RuntimeError(f'dashboard compatibility checks failed: {checks}')

    print('4B.4.3.6.6.20a dashboard compatibility restore patch applied')
    print(f' - compat_block_inserted: {inserted}')
    print(f' - extract_training_output_path_replaced: {replaced_extract}')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
