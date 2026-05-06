from __future__ import annotations

from pathlib import Path

START = '# BEGIN 4B.4.3.6.6.20S RESTORE POSITION TEXT CONTRACT'
END = '# END 4B.4.3.6.6.20S RESTORE POSITION TEXT CONTRACT'

BLOCK = '''
# BEGIN 4B.4.3.6.6.20S RESTORE POSITION TEXT CONTRACT
# Restores the top-level build_position_management_text import contract removed by 20R.
from typing import Any as _TB20SAny


def _tb20s_dict(value: _TB20SAny) -> dict[str, _TB20SAny]:
    return value if isinstance(value, dict) else {}


def _tb20s_bool(value: _TB20SAny, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {'1', 'true', 'yes', 'on', 'enabled', 'ready'}:
            return True
        if raw in {'0', 'false', 'no', 'off', 'disabled', 'blocked'}:
            return False
    return bool(value)


def _tb20s_float(value: _TB20SAny, default: float = 0.0) -> float:
    try:
        if value is None or value == '':
            return default
        return float(value)
    except Exception:
        return default


def _tb20s_fmt(value: _TB20SAny, digits: int = 4) -> str:
    try:
        if value is None:
            return '-'
        return f'{float(value):.{int(digits)}f}'
    except Exception:
        return '-' if value in (None, '') else str(value)


def _tb20s_fmt_pct(value: _TB20SAny) -> str:
    if value is None:
        return '-'
    numeric = _tb20s_float(value)
    if abs(numeric) <= 1.0:
        numeric *= 100.0
    return f'{numeric:.2f}%'


def _tb20s_position_payload(payload: dict[str, _TB20SAny] | None) -> dict[str, _TB20SAny]:
    payload = _tb20s_dict(payload)
    return _tb20s_dict(payload.get('position_snapshot') or payload.get('position') or payload)


def build_position_management_text(status_or_position: dict[str, _TB20SAny] | None = None) -> str:
    position = _tb20s_position_payload(status_or_position)
    protective = _tb20s_dict(position.get('protective_exit'))
    risk_plan = _tb20s_dict(position.get('risk_plan'))
    risk_exec = _tb20s_dict(protective.get('risk_execution') or position.get('risk_execution'))

    qty = _tb20s_float(position.get('qty') or position.get('quantity'), 0.0)
    present = _tb20s_bool(position.get('present')) or qty > 0.0
    position_is_dust = _tb20s_bool(
        position.get('position_is_dust')
        if 'position_is_dust' in position
        else position.get('is_dust', protective.get('is_dust', protective.get('position_is_dust')))
    )
    protective_ready = _tb20s_bool(protective.get('protective_exit_ready'), default=False)
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

    return '\n'.join([
        f"Position status : {'IN_POSITION' if present else 'FLAT'}",
        f"Position source : {position.get('source') or '-'}",
        f"Qty             : {_tb20s_fmt(qty, 8)}",
        f"Entry           : {_tb20s_fmt(position.get('entry_price'), 4)}",
        f"Mark            : {_tb20s_fmt(position.get('mark_price'), 4)}",
        f"Unrealized PnL  : {_tb20s_fmt(position.get('unrealized_pnl'), 6)}",
        f"Unrealized %    : {_tb20s_fmt_pct(position.get('unrealized_pnl_pct'))}",
        f"Protective exit : {'READY' if protective_ready else 'BLOCKED'} / {block_reason}",
        f"Exit qty        : {_tb20s_fmt(protective.get('tradable_exit_qty'), 8)}",
        f"Exit notional   : {_tb20s_fmt(protective.get('exit_notional'), 4)}",
        f"Dust position   : {'YES' if position_is_dust else 'NO'}",
        f"Risk plan       : {'READY' if risk_plan or protective or risk_exec else 'MISSING'}",
        f"Stop loss       : {_tb20s_fmt(stop_loss, 4)}",
        f"Effective SL    : {_tb20s_fmt(effective_sl, 4)}",
        f"Active stop     : {_tb20s_fmt(active_stop, 4)}",
        f"Take profit     : {_tb20s_fmt(take_profit, 4)}",
        f"Dist. to SL     : {_tb20s_fmt(protective.get('distance_to_stop'), 4)} ({_tb20s_fmt_pct(protective.get('distance_to_stop_pct'))})",
        f"Dist. to TP     : {_tb20s_fmt(protective.get('distance_to_take_profit'), 4)} ({_tb20s_fmt_pct(protective.get('distance_to_take_profit_pct'))})",
        f"Break-even      : {_tb20s_bool(protective.get('break_even_armed') or risk_exec.get('break_even_armed') or risk_plan.get('break_even_moved'))} / trg {_tb20s_fmt(protective.get('break_even_trigger_price') or risk_plan.get('break_even_trigger_price'), 4)}",
        f"Trailing        : {_tb20s_bool(protective.get('trailing_enabled') or risk_plan.get('trailing_enabled'))} / armed {_tb20s_bool(protective.get('trailing_armed') or risk_exec.get('trailing_armed') or risk_plan.get('trailing_armed'))} / stop {_tb20s_fmt(protective.get('trailing_stop') or risk_exec.get('trailing_stop') or risk_plan.get('trailing_stop'), 4)}",
        f"Partial TP      : {_tb20s_fmt(partial_price, 4)} / {_tb20s_fmt(partial_pct, 2)} / hit {_tb20s_bool(partial_done)}",
        f"Partial TP done : {_tb20s_bool(partial_done)}",
        f"Risk exec       : {exec_status} / {exec_signal}",
        f"Risk exit       : {exit_action} / {exit_reason}",
    ])
# END 4B.4.3.6.6.20S RESTORE POSITION TEXT CONTRACT
'''


def patch_text(text: str) -> str:
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        return before + '\n\n' + BLOCK.strip() + '\n\n' + after
    return text.rstrip() + '\n\n' + BLOCK.strip() + '\n'


def main() -> int:
    dashboard = Path.cwd() / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
    if not dashboard.exists():
        raise RuntimeError(f'dashboard.py not found: {dashboard}')
    original = dashboard.read_text(encoding='utf-8')
    updated = patch_text(original)
    dashboard.write_text(updated, encoding='utf-8')
    checks = {
        'build_position_management_text_present': 'def build_position_management_text' in updated,
        'protective_exit_ready_text': "Protective exit : {'READY'" in updated,
        'effective_sl_text': 'Effective SL' in updated,
        'take_profit_text': 'Take profit' in updated,
        'partial_tp_done_text': 'Partial TP done' in updated,
        'risk_exec_text': 'Risk exec' in updated,
    }
    print('4B.4.3.6.6.20s restore position text contract applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(checks.values()):
        raise RuntimeError(f'20s verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
