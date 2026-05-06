from __future__ import annotations

import py_compile
from pathlib import Path

OLD_START = '# BEGIN 4B.4.3.6.6.20S RESTORE POSITION TEXT CONTRACT'
OLD_END = '# END 4B.4.3.6.6.20S RESTORE POSITION TEXT CONTRACT'
NEW_START = '# BEGIN 4B.4.3.6.6.20S2 SYNTAX SAFE POSITION TEXT CONTRACT'
NEW_END = '# END 4B.4.3.6.6.20S2 SYNTAX SAFE POSITION TEXT CONTRACT'

BLOCK = r'''
# BEGIN 4B.4.3.6.6.20S2 SYNTAX SAFE POSITION TEXT CONTRACT
# Syntax-safe restore for the top-level build_position_management_text contract.
# This block intentionally avoids single-quoted '\n' literals to prevent the
# broken 20S unterminated-string regression.
from typing import Any as _TB20S2Any


def _tb20s2_dict(value: _TB20S2Any) -> dict[str, _TB20S2Any]:
    return value if isinstance(value, dict) else {}


def _tb20s2_bool(value: _TB20S2Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {'1', 'true', 'yes', 'on', 'enabled', 'ready'}:
            return True
        if raw in {'0', 'false', 'no', 'off', 'disabled', 'blocked'}:
            return False
    return bool(value)


def _tb20s2_float(value: _TB20S2Any, default: float = 0.0) -> float:
    try:
        if value is None or value == '':
            return default
        return float(value)
    except Exception:
        return default


def _tb20s2_fmt(value: _TB20S2Any, digits: int = 4) -> str:
    try:
        if value is None:
            return '-'
        return f'{float(value):.{int(digits)}f}'
    except Exception:
        return '-' if value in (None, '') else str(value)


def _tb20s2_fmt_pct(value: _TB20S2Any) -> str:
    if value is None:
        return '-'
    numeric = _tb20s2_float(value)
    if abs(numeric) <= 1.0:
        numeric *= 100.0
    return f'{numeric:.2f}%'


def _tb20s2_position_payload(payload: dict[str, _TB20S2Any] | None) -> dict[str, _TB20S2Any]:
    payload = _tb20s2_dict(payload)
    return _tb20s2_dict(payload.get('position_snapshot') or payload.get('position') or payload)


def build_position_management_text(status_or_position: dict[str, _TB20S2Any] | None = None) -> str:
    position = _tb20s2_position_payload(status_or_position)
    protective = _tb20s2_dict(position.get('protective_exit'))
    risk_plan = _tb20s2_dict(position.get('risk_plan'))
    risk_exec = _tb20s2_dict(protective.get('risk_execution') or position.get('risk_execution'))

    qty = _tb20s2_float(position.get('qty') or position.get('quantity'), 0.0)
    present = _tb20s2_bool(position.get('present')) or qty > 0.0
    position_is_dust = _tb20s2_bool(
        position.get('position_is_dust')
        if 'position_is_dust' in position
        else position.get('is_dust', protective.get('is_dust', protective.get('position_is_dust')))
    )
    protective_ready = _tb20s2_bool(protective.get('protective_exit_ready'), default=False)
    block_reason = protective.get('block_reason') or '-'

    stop_loss = protective.get('stop_loss') or risk_plan.get('stop_loss')
    effective_sl = (
        risk_exec.get('effective_stop_loss')
        or risk_exec.get('active_stop_loss')
        or protective.get('active_stop_loss')
        or risk_plan.get('active_stop_loss')
        or stop_loss
    )
    take_profit = protective.get('take_profit') or risk_plan.get('take_profit')
    active_stop = protective.get('active_stop_loss') or risk_exec.get('active_stop_loss') or risk_plan.get('active_stop_loss') or effective_sl

    partial_done = (
        risk_plan.get('partial_tp_done')
        if 'partial_tp_done' in risk_plan
        else risk_plan.get('partial_tp_hit', protective.get('partial_tp_triggered', risk_exec.get('partial_tp_done', risk_exec.get('partial_tp_triggered', False))))
    )
    partial_price = protective.get('partial_tp_price') or risk_plan.get('partial_tp_price')
    partial_pct = protective.get('partial_tp_close_pct') or risk_plan.get('partial_tp_close_pct')

    exec_status = str(risk_exec.get('status') or ('READY' if present and not position_is_dust else 'BLOCKED' if not present else 'READY'))
    exec_signal = str(risk_exec.get('exit_signal') or risk_exec.get('exit_action') or 'HOLD')
    exit_action = risk_exec.get('exit_action') or risk_exec.get('action') or 'NONE'
    exit_reason = risk_exec.get('exit_reason') or risk_exec.get('reason') or block_reason or '-'

    lines = [
        f"Position status : {'IN_POSITION' if present else 'FLAT'}",
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_tb20s2_fmt(qty, 8)}",
        f"Entry           : {_tb20s2_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_tb20s2_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_tb20s2_fmt(position.get('unrealized_pnl'), 6)}",
        f"Unrealized %    : {_tb20s2_fmt_pct(position.get('unrealized_pnl_pct'))}",
        f"Protective exit : {'READY' if protective_ready else 'BLOCKED'} / {block_reason}",
        f"Exit qty        : {_tb20s2_fmt(protective.get('tradable_exit_qty'), 8)}",
        f"Exit notional   : {_tb20s2_fmt(protective.get('exit_notional'), 4)}",
        f"Dust position   : {'YES' if position_is_dust else 'NO'}",
        f"Risk plan       : {'READY' if risk_plan or protective or risk_exec else 'MISSING'}",
        f"Stop loss       : {_tb20s2_fmt(stop_loss, 4)}",
        f"Effective SL    : {_tb20s2_fmt(effective_sl, 4)}",
        f"Active stop     : {_tb20s2_fmt(active_stop, 4)}",
        f"Take profit     : {_tb20s2_fmt(take_profit, 4)}",
        f"Dist. to SL     : {_tb20s2_fmt(protective.get('distance_to_stop'), 4)} ({_tb20s2_fmt_pct(protective.get('distance_to_stop_pct'))})",
        f"Dist. to TP     : {_tb20s2_fmt(protective.get('distance_to_take_profit'), 4)} ({_tb20s2_fmt_pct(protective.get('distance_to_take_profit_pct'))})",
        f"Break-even      : {_tb20s2_bool(protective.get('break_even_armed') or risk_exec.get('break_even_armed') or risk_plan.get('break_even_moved'))} / trg {_tb20s2_fmt(protective.get('break_even_trigger_price') or risk_plan.get('break_even_trigger_price'), 4)}",
        f"Trailing        : {_tb20s2_bool(protective.get('trailing_enabled') or risk_plan.get('trailing_enabled'))} / armed {_tb20s2_bool(protective.get('trailing_armed') or risk_exec.get('trailing_armed') or risk_plan.get('trailing_armed'))} / stop {_tb20s2_fmt(protective.get('trailing_stop') or risk_exec.get('trailing_stop') or risk_plan.get('trailing_stop'), 4)}",
        f"Partial TP      : {_tb20s2_fmt(partial_price, 4)} / {_tb20s2_fmt(partial_pct, 2)} / hit {_tb20s2_bool(partial_done)}",
        f"Partial TP done : {_tb20s2_bool(partial_done)}",
        f"Risk exec       : {exec_status} / {exec_signal}",
        f"Risk exit       : {exit_action} / {exit_reason}",
    ]
    return "\\n".join(lines)
# END 4B.4.3.6.6.20S2 SYNTAX SAFE POSITION TEXT CONTRACT
'''


def remove_block(text: str, start: str, end: str) -> tuple[str, int]:
    count = 0
    while start in text and end in text and text.index(start) < text.index(end):
        before, rest = text.split(start, 1)
        _middle, after = rest.split(end, 1)
        text = before.rstrip() + '\n\n' + after.lstrip()
        count += 1
    return text, count


def patch_text(text: str) -> tuple[str, dict[str, int | bool]]:
    text, removed_20s = remove_block(text, OLD_START, OLD_END)
    text, removed_20s2 = remove_block(text, NEW_START, NEW_END)
    text = text.rstrip() + '\n\n' + BLOCK.strip() + '\n'
    checks: dict[str, int | bool] = {
        'removed_broken_20s_blocks': removed_20s,
        'removed_old_20s2_blocks': removed_20s2,
        'return_newline_join_safe': 'return "\\\\n".join(lines)' in text,
        'unterminated_return_marker_absent': "return '\\n" not in text and "return '\r\n" not in text,
        'build_position_management_text_present': 'def build_position_management_text' in text,
        'effective_sl_text': 'Effective SL' in text,
        'take_profit_text': 'Take profit' in text,
        'partial_tp_done_text': 'Partial TP done' in text,
        'risk_exec_text': 'Risk exec' in text,
    }
    return text, checks


def main() -> int:
    dashboard = Path.cwd() / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
    if not dashboard.exists():
        raise RuntimeError(f'dashboard.py not found: {dashboard}')
    original = dashboard.read_text(encoding='utf-8')
    updated, checks = patch_text(original)
    dashboard.write_text(updated, encoding='utf-8')
    py_compile.compile(str(dashboard), doraise=True)
    print('4B.4.3.6.6.20s2 repair dashboard syntax + position text applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    required = [
        'return_newline_join_safe',
        'unterminated_return_marker_absent',
        'build_position_management_text_present',
        'effective_sl_text',
        'take_profit_text',
        'partial_tp_done_text',
        'risk_exec_text',
    ]
    if not all(bool(checks[key]) for key in required):
        raise RuntimeError(f'20s2 verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
