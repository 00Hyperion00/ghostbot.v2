from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def patch_models() -> list[str]:
    path = "src/tradebot/models.py"
    s = read(path)
    changes: list[str] = []
    if "startup_hygiene:" not in s:
        if "    dust_snapshot: dict[str, float] = field(default_factory=dict)\n" in s:
            s = s.replace(
                "    dust_snapshot: dict[str, float] = field(default_factory=dict)\n",
                "    dust_snapshot: dict[str, float] = field(default_factory=dict)\n"
                "    startup_hygiene: dict[str, Any] = field(default_factory=dict)\n",
            )
        elif "    last_order_event: str" in s:
            s = re.sub(
                r"(    last_order_event: str[^\n]*\n)",
                r"\1    startup_hygiene: dict[str, Any] = field(default_factory=dict)\n",
                s,
                count=1,
            )
        else:
            raise RuntimeError("RuntimeState insertion point not found in models.py")
        changes.append("models.RuntimeState.startup_hygiene")
    write(path, s)
    return changes


def patch_engine() -> list[str]:
    path = "src/tradebot/engine.py"
    s = read(path)
    changes: list[str] = []

    # Keep public /status risk_plan backward-compatible. New execution state stays under protective_exit.risk_execution.
    risk_plan_block = re.compile(
        r"        if position\.risk_plan is not None:\n"
        r"            risk_plan_dict = \{.*?\n"
        r"            \}\n"
        r"        else:\n"
        r"            risk_plan_dict = None\n",
        re.DOTALL,
    )
    simple_risk_plan_block = """        if position.risk_plan is not None:
            risk_plan_dict = {
                'atr': position.risk_plan.atr,
                'entry_price': position.risk_plan.entry_price,
                'stop_loss': position.risk_plan.stop_loss,
                'take_profit': position.risk_plan.take_profit,
                'open_risk_quote': position.risk_plan.open_risk_quote,
                'planned_rr': position.risk_plan.planned_rr,
                'break_even_trigger_price': position.risk_plan.break_even_trigger_price,
                'break_even_stop_price': position.risk_plan.break_even_stop_price,
                'trailing_enabled': position.risk_plan.trailing_enabled,
                'partial_tp_price': position.risk_plan.partial_tp_price,
                'partial_tp_close_pct': position.risk_plan.partial_tp_close_pct,
            }
        else:
            risk_plan_dict = None
"""
    s2, n = risk_plan_block.subn(simple_risk_plan_block, s, count=1)
    if n:
        s = s2
        changes.append("engine.risk_plan_backward_compatible_dict")

    # Time-stop support and legacy snapshot aliases expected by local tests.
    if "position_max_hold_sec = int(getattr(self.settings, 'position_max_hold_sec'" not in s:
        marker = """        partial_tp_hit = partial_enabled and partial_tp_price is not None and mark_price >= float(partial_tp_price) and not risk_plan.partial_tp_triggered
        stop_hit = active_stop is not None and mark_price <= float(active_stop)
        take_profit_hit = take_profit is not None and mark_price >= float(take_profit)
"""
        replacement = """        partial_tp_hit = partial_enabled and partial_tp_price is not None and mark_price >= float(partial_tp_price) and not risk_plan.partial_tp_triggered
        position_max_hold_sec = int(getattr(self.settings, 'position_max_hold_sec', 0) or 0)
        opened_at = getattr(position, 'opened_at', None)
        time_stop_hit = False
        if position_max_hold_sec > 0 and opened_at:
            try:
                time_stop_hit = (now - int(opened_at)) >= (position_max_hold_sec * 1000)
            except Exception:
                time_stop_hit = False
        stop_hit = active_stop is not None and mark_price <= float(active_stop)
        take_profit_hit = take_profit is not None and mark_price >= float(take_profit)
"""
        if marker in s:
            s = s.replace(marker, replacement, 1)
            changes.append("engine.time_stop_eval")
        else:
            raise RuntimeError("risk execution partial_tp/stop marker not found")

    if "if time_stop_hit:\n            exit_reason = 'TIME_STOP_HIT'" not in s:
        marker = """        if stop_hit:
            exit_reason = 'STOP_LOSS_HIT' if active_stop == stop_loss else 'TRAILING_STOP_HIT'
            exit_action = 'FULL_EXIT'
            requested_exit_qty = float(position.qty or 0.0)
        elif take_profit_hit:
"""
        replacement = """        if time_stop_hit:
            exit_reason = 'TIME_STOP_HIT'
            exit_action = 'FULL_EXIT'
            requested_exit_qty = float(position.qty or 0.0)
        elif stop_hit:
            exit_reason = 'STOP_LOSS_HIT' if active_stop == stop_loss else 'TRAILING_STOP_HIT'
            exit_action = 'FULL_EXIT'
            requested_exit_qty = float(position.qty or 0.0)
        elif take_profit_hit:
"""
        if marker in s:
            s = s.replace(marker, replacement, 1)
            changes.append("engine.time_stop_priority")
        else:
            raise RuntimeError("risk execution priority marker not found")

    if "'status': 'TRIGGERED' if exit_reason is not None else 'READY'" not in s:
        s = s.replace(
            "            'exit_action': exit_action,\n",
            "            'exit_action': exit_action,\n"
            "            'status': 'TRIGGERED' if exit_reason is not None else 'READY',\n"
            "            'exit_signal': exit_action if exit_reason is not None else 'HOLD',\n",
            1,
        )
        changes.append("engine.risk_snapshot_status_aliases")

    if "'effective_stop_loss': active_stop" not in s:
        s = s.replace(
            "            'active_stop_loss': active_stop,\n",
            "            'active_stop_loss': active_stop,\n"
            "            'effective_stop_loss': active_stop,\n",
            1,
        )
        changes.append("engine.effective_stop_loss_alias")

    if "'partial_tp_done': bool(risk_plan.partial_tp_triggered)" not in s:
        s = s.replace(
            "            'partial_tp_triggered': bool(risk_plan.partial_tp_triggered),\n",
            "            'partial_tp_triggered': bool(risk_plan.partial_tp_triggered),\n"
            "            'partial_tp_done': bool(risk_plan.partial_tp_triggered),\n",
            1,
        )
        changes.append("engine.partial_tp_done_alias")

    if "'position_max_hold_sec': position_max_hold_sec" not in s:
        s = s.replace(
            "            'events': events,\n",
            "            'position_max_hold_sec': position_max_hold_sec,\n"
            "            'time_stop_hit': bool(time_stop_hit),\n"
            "            'events': events,\n",
            1,
        )
        changes.append("engine.position_max_hold_snapshot")

    # Non-present snapshots should also be consumable by dashboard/tests.
    s = s.replace(
        "                'exit_action': 'NONE',\n                'block_reason': 'POSITION_NOT_FOUND',\n",
        "                'exit_action': 'NONE',\n                'status': 'NO_POSITION',\n                'exit_signal': 'HOLD',\n                'effective_stop_loss': None,\n                'partial_tp_done': False,\n                'position_max_hold_sec': int(getattr(self.settings, 'position_max_hold_sec', 0) or 0),\n                'block_reason': 'POSITION_NOT_FOUND',\n",
    )
    s = s.replace(
        "                'exit_action': 'NONE',\n                'block_reason': 'RISK_PLAN_MISSING',\n",
        "                'exit_action': 'NONE',\n                'status': 'RISK_PLAN_MISSING',\n                'exit_signal': 'HOLD',\n                'effective_stop_loss': None,\n                'partial_tp_done': False,\n                'position_max_hold_sec': int(getattr(self.settings, 'position_max_hold_sec', 0) or 0),\n                'block_reason': 'RISK_PLAN_MISSING',\n",
    )

    write(path, s)
    return changes


def patch_dashboard() -> list[str]:
    path = "src/tradebot/ui/dashboard.py"
    s = read(path)
    changes: list[str] = []

    replacements = {
        "widget = getattr(self, widget_name, None)": "widget = safe_obj_getattr(self, widget_name, None)",
        "connected=bool(getattr(self, 'last_connected', True))": "connected=bool(safe_obj_getattr(self, 'last_connected', True))",
        "getattr(self, '_last_audit_payload', {})": "safe_obj_getattr(self, '_last_audit_payload', {})",
        "enabled_style = getattr(self, '_button_style_enabled', {": "enabled_style = safe_obj_getattr(self, '_button_style_enabled', {",
        "disabled_style = getattr(self, '_button_style_disabled', {": "disabled_style = safe_obj_getattr(self, '_button_style_disabled', {",
    }
    for old, new in replacements.items():
        if old in s:
            s = s.replace(old, new)
            changes.append(f"dashboard.safe_getattr:{old[:32]}")

    if "risk_exec = protective.get('risk_execution') or position.get('risk_execution') or {}" not in s:
        s = s.replace(
            "risk_exec = protective.get('risk_execution') or {}",
            "risk_exec = protective.get('risk_execution') or position.get('risk_execution') or {}",
        )
        changes.append("dashboard.risk_exec_top_level_fallback")

    if "Risk exec       :" not in s:
        marker = "        f'Risk exit       : {risk_exec.get(\"exit_action\") or \"NONE\"} / {risk_exec.get(\"exit_reason\") or protective.get(\"last_exit_reason\") or \"-\"}',\n"
        insert = "        f'Risk exec       : {risk_exec.get(\"status\") or (\"READY\" if risk_exec.get(\"ready\") else \"-\")} / {risk_exec.get(\"exit_signal\") or (\"HOLD\" if not risk_exec.get(\"exit_required\") else risk_exec.get(\"exit_action\")) or \"-\"}',\n"
        if marker in s:
            s = s.replace(marker, insert + marker, 1)
            changes.append("dashboard.risk_exec_line")
        else:
            # Compatible with older wording: add before the closing list when Partial TP line exists.
            marker2 = "        f'Partial TP      : {_fmt_float(protective.get(\"partial_tp_price\"), 4)} / {_fmt_pct(protective.get(\"partial_tp_close_pct\"))} / hit {bool(protective.get(\"partial_tp_triggered\") or risk_exec.get(\"partial_tp_triggered\"))}',\n"
            if marker2 in s:
                s = s.replace(marker2, marker2 + insert, 1)
                changes.append("dashboard.risk_exec_line_fallback")

    write(path, s)
    return changes


def patch_tests() -> list[str]:
    changes: list[str] = []
    path = ROOT / "tests/test_runtime_observability_event_audit.py"
    if path.exists():
        s = path.read_text(encoding="utf-8")
        s2 = s.replace("4B.4.3.6.6.10", "4B.4.3.6.6.11")
        if s2 != s:
            path.write_text(s2, encoding="utf-8")
            changes.append("tests.runtime_observability_contract_11")
    return changes


def main() -> None:
    all_changes: list[str] = []
    for fn in (patch_models, patch_engine, patch_dashboard, patch_tests):
        all_changes.extend(fn())
    print("4B.4.3.6.6.11b hotfix applied")
    if all_changes:
        for item in all_changes:
            print(f" - {item}")
    else:
        print(" - no changes needed; files already compatible")


if __name__ == "__main__":
    main()
