from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding='utf-8')


def patch_engine() -> list[str]:
    path = 'src/tradebot/engine.py'
    s = read(path)
    changes: list[str] = []

    # Legacy partial TP contract expected by tests/dashboard.
    if "'suggested_close_pct':" not in s:
        markers = [
            "            'suggested_exit_qty': requested_exit_qty,\n",
            '            "suggested_exit_qty": requested_exit_qty,\n',
        ]
        for marker in markers:
            if marker in s:
                insert = marker + "            'suggested_close_pct': (float(risk_plan.partial_tp_close_pct or 0.0) if exit_reason == 'PARTIAL_TP_HIT' else None),\n"
                s = s.replace(marker, insert, 1)
                changes.append('engine.suggested_close_pct_alias')
                break
        else:
            # Fallback: insert next to requested_exit_qty if 11c did not add suggested_exit_qty.
            marker = "            'requested_exit_qty': requested_exit_qty,\n"
            if marker not in s:
                raise RuntimeError('risk snapshot requested_exit_qty marker not found for suggested_close_pct')
            s = s.replace(
                marker,
                marker
                + "            'suggested_exit_qty': requested_exit_qty,\n"
                + "            'suggested_close_pct': (float(risk_plan.partial_tp_close_pct or 0.0) if exit_reason == 'PARTIAL_TP_HIT' else None),\n",
                1,
            )
            changes.append('engine.suggested_exit_qty_and_close_pct_alias')

    # Ensure the non-present/missing aliases also have suggested_close_pct so JSON shape is stable.
    if "'suggested_close_pct': None" not in s:
        s = s.replace(
            "                'suggested_exit_qty': 0.0,\n                'position_max_hold_sec': int(getattr(self.settings, 'position_max_hold_sec', 0) or 0),\n",
            "                'suggested_exit_qty': 0.0,\n                'suggested_close_pct': None,\n                'position_max_hold_sec': int(getattr(self.settings, 'position_max_hold_sec', 0) or 0),\n",
        )
        changes.append('engine.stable_missing_suggested_close_pct_alias')

    write(path, s)
    return changes


def patch_dashboard() -> list[str]:
    path = 'src/tradebot/ui/dashboard.py'
    s = read(path)
    changes: list[str] = []

    if 'safe_obj_safe_obj_getattr' in s:
        s = s.replace('safe_obj_safe_obj_getattr', 'safe_obj_getattr')
        changes.append('dashboard.fix_double_safe_getattr_global')

    # Tk/CustomTk __new__ probes route unknown getattr() through tkinter __getattr__, causing recursion.
    button_names = [
        'btn_start',
        'btn_stop',
        'btn_force_buy',
        'btn_force_sell',
        'btn_cancel_pending',
        'btn_sync_balances',
        'btn_risk_reset',
        'btn_safe_mode',
        'btn_train_model',
        'btn_reload_ai',
    ]
    for name in button_names:
        old = f"getattr(self, '{name}', None)"
        new = f"safe_obj_getattr(self, '{name}', None)"
        if old in s:
            s = s.replace(old, new)
            changes.append(f'dashboard.safe_button_getattr:{name}')

    unsafe_replacements = {
        "getattr(self, '_last_connected', True)": "safe_obj_getattr(self, '_last_connected', True)",
        'getattr(self, "_last_connected", True)': 'safe_obj_getattr(self, "_last_connected", True)',
        "getattr(self, '_last_audit_payload', {})": "safe_obj_getattr(self, '_last_audit_payload', {})",
        'getattr(self, "_last_audit_payload", {})': 'safe_obj_getattr(self, "_last_audit_payload", {})',
        "widget = getattr(self, widget_name, None)": "widget = safe_obj_getattr(self, widget_name, None)",
    }
    for old, new in unsafe_replacements.items():
        if old in s:
            s = s.replace(old, new)
            changes.append(f'dashboard.safe_getattr:{old[:40]}')

    # Dashboard risk execution UX contract expected by tests.
    if 'Partial TP done' not in s:
        partial_done_line = "        f'Partial TP done : {bool(risk_exec.get(\"partial_tp_done\") or risk_exec.get(\"partial_tp_triggered\") or protective.get(\"partial_tp_triggered\"))}',\n"
        markers = [
            "        f'Risk exec       : {risk_exec.get(\"status\") or (\"READY\" if risk_exec.get(\"ready\") else \"-\")} / {risk_exec.get(\"exit_signal\") or (\"HOLD\" if not risk_exec.get(\"exit_required\") else risk_exec.get(\"exit_action\")) or \"-\"}',\n",
            "        f'Risk exit       : {risk_exec.get(\"exit_action\") or \"NONE\"} / {risk_exec.get(\"exit_reason\") or protective.get(\"last_exit_reason\") or \"-\"}',\n",
            "        f'Effective SL    : {_fmt_float(risk_exec.get(\"effective_stop_loss\") or protective.get(\"active_stop_loss\") or risk_plan.get(\"stop_loss\"), 4)}',\n",
        ]
        for marker in markers:
            if marker in s:
                s = s.replace(marker, partial_done_line + marker, 1)
                changes.append('dashboard.partial_tp_done_line')
                break
        else:
            raise RuntimeError('dashboard insertion marker not found for Partial TP done')

    write(path, s)
    return changes


def main() -> None:
    all_changes: list[str] = []
    for fn in (patch_engine, patch_dashboard):
        all_changes.extend(fn())
    print('4B.4.3.6.6.11d hotfix applied')
    if all_changes:
        for item in all_changes:
            print(f' - {item}')
    else:
        print(' - no changes needed')


if __name__ == '__main__':
    main()
