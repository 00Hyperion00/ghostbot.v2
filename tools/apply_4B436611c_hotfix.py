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

    if "break_even_moved:" not in s:
        anchors = [
            "    break_even_armed: bool = False\n",
            "    break_even_stop_price: float | None = None\n",
        ]
        for anchor in anchors:
            if anchor in s:
                s = s.replace(anchor, anchor + "    break_even_moved: bool = False\n", 1)
                changes.append("models.RiskPlan.break_even_moved")
                break
        else:
            raise RuntimeError("RiskPlan insertion point not found for break_even_moved")

    if "startup_hygiene:" not in s:
        if "    dust_snapshot: dict[str, float] = field(default_factory=dict)\n" in s:
            s = s.replace(
                "    dust_snapshot: dict[str, float] = field(default_factory=dict)\n",
                "    dust_snapshot: dict[str, float] = field(default_factory=dict)\n"
                "    startup_hygiene: dict[str, Any] = field(default_factory=dict)\n",
                1,
            )
        elif "    last_order_event:" in s:
            s = re.sub(
                r"(    last_order_event:[^\n]*\n)",
                r"\1    startup_hygiene: dict[str, Any] = field(default_factory=dict)\n",
                s,
                count=1,
            )
        else:
            raise RuntimeError("RuntimeState insertion point not found for startup_hygiene")
        changes.append("models.RuntimeState.startup_hygiene")

    write(path, s)
    return changes


def patch_engine() -> list[str]:
    path = "src/tradebot/engine.py"
    s = read(path)
    changes: list[str] = []

    # Public position_snapshot.risk_plan must stay legacy-compatible. Runtime payload may contain
    # new dataclass fields, so do not prefer payload_position['risk_plan'] over this curated dict.
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
        changes.append("engine.curated_risk_plan_dict")

    if "risk_plan = payload_position.get('risk_plan') or risk_plan_dict" in s:
        s = s.replace("risk_plan = payload_position.get('risk_plan') or risk_plan_dict", "risk_plan = risk_plan_dict", 1)
        changes.append("engine.ignore_payload_risk_plan_state_fields")
    if 'risk_plan = payload_position.get("risk_plan") or risk_plan_dict' in s:
        s = s.replace('risk_plan = payload_position.get("risk_plan") or risk_plan_dict', 'risk_plan = risk_plan_dict', 1)
        changes.append("engine.ignore_payload_risk_plan_state_fields_doublequote")

    # Legacy test contract aliases for risk execution snapshot.
    if "'should_submit_exit': exit_reason is not None" not in s:
        if "            'exit_signal': exit_action if exit_reason is not None else 'HOLD',\n" in s:
            s = s.replace(
                "            'exit_signal': exit_action if exit_reason is not None else 'HOLD',\n",
                "            'exit_signal': exit_action if exit_reason is not None else 'HOLD',\n"
                "            'should_submit_exit': exit_reason is not None,\n",
                1,
            )
        elif "            'exit_action': exit_action,\n" in s:
            s = s.replace(
                "            'exit_action': exit_action,\n",
                "            'exit_action': exit_action,\n"
                "            'status': 'TRIGGERED' if exit_reason is not None else 'READY',\n"
                "            'exit_signal': exit_action if exit_reason is not None else 'HOLD',\n"
                "            'should_submit_exit': exit_reason is not None,\n",
                1,
            )
        else:
            raise RuntimeError("risk snapshot exit_action marker not found")
        changes.append("engine.should_submit_exit_alias")

    if "'suggested_exit_qty': requested_exit_qty" not in s:
        if "            'requested_exit_qty': requested_exit_qty,\n" not in s:
            raise RuntimeError("requested_exit_qty marker not found")
        s = s.replace(
            "            'requested_exit_qty': requested_exit_qty,\n",
            "            'requested_exit_qty': requested_exit_qty,\n"
            "            'suggested_exit_qty': requested_exit_qty,\n",
            1,
        )
        changes.append("engine.suggested_exit_qty_alias")

    if "'break_even_moved': bool(getattr(risk_plan, 'break_even_moved', False))" not in s:
        if "            'break_even_armed': bool(risk_plan.break_even_armed),\n" in s:
            s = s.replace(
                "            'break_even_armed': bool(risk_plan.break_even_armed),\n",
                "            'break_even_armed': bool(risk_plan.break_even_armed),\n"
                "            'break_even_moved': bool(getattr(risk_plan, 'break_even_moved', False)),\n",
                1,
            )
            changes.append("engine.break_even_moved_snapshot")

    # Mutating BE state must update the legacy field too. Use getattr/setattr because old objects may be loaded.
    if "setattr(risk_plan, 'break_even_moved', True)" not in s:
        marker = "                    risk_plan.break_even_armed = True\n"
        if marker in s:
            s = s.replace(marker, marker + "                    setattr(risk_plan, 'break_even_moved', True)\n", 1)
            changes.append("engine.break_even_moved_mutation")
        else:
            # Fallback: place after RISK_BREAK_EVEN_ARMED log preparation if code shape changed.
            marker2 = "                events.append('BREAK_EVEN_ARMED')\n"
            if marker2 in s:
                s = s.replace(marker2, marker2 + "                if mutate:\n                    setattr(risk_plan, 'break_even_moved', True)\n", 1)
                changes.append("engine.break_even_moved_mutation_fallback")

    # Non-present/missing snapshots should also expose aliases.
    s = s.replace(
        "                'partial_tp_done': False,\n                'position_max_hold_sec': int(getattr(self.settings, 'position_max_hold_sec', 0) or 0),\n",
        "                'partial_tp_done': False,\n                'should_submit_exit': False,\n                'suggested_exit_qty': 0.0,\n                'position_max_hold_sec': int(getattr(self.settings, 'position_max_hold_sec', 0) or 0),\n",
    )

    write(path, s)
    return changes


def patch_dashboard() -> list[str]:
    path = "src/tradebot/ui/dashboard.py"
    s = read(path)
    changes: list[str] = []

    if "safe_obj_safe_obj_getattr" in s:
        s = s.replace("safe_obj_safe_obj_getattr", "safe_obj_getattr")
        changes.append("dashboard.fix_double_safe_getattr")

    replacements = {
        "widget = getattr(self, widget_name, None)": "widget = safe_obj_getattr(self, widget_name, None)",
        "connected=bool(getattr(self, '_last_connected', True))": "connected=bool(safe_obj_getattr(self, '_last_connected', True))",
        "connected=bool(getattr(self, 'last_connected', True))": "connected=bool(safe_obj_getattr(self, 'last_connected', True))",
        "getattr(self, '_last_audit_payload', {})": "safe_obj_getattr(self, '_last_audit_payload', {})",
        "enabled_style = getattr(self, '_button_style_enabled', {": "enabled_style = safe_obj_getattr(self, '_button_style_enabled', {",
        "disabled_style = getattr(self, '_button_style_disabled', {": "disabled_style = safe_obj_getattr(self, '_button_style_disabled', {",
    }
    for old, new in replacements.items():
        if old in s:
            s = s.replace(old, new)
            changes.append(f"dashboard.safe_getattr:{old[:36]}")

    if "risk_exec = protective.get('risk_execution') or position.get('risk_execution') or {}" not in s:
        s = s.replace(
            "risk_exec = protective.get('risk_execution') or {}",
            "risk_exec = protective.get('risk_execution') or position.get('risk_execution') or {}",
        )
        changes.append("dashboard.risk_exec_top_level_fallback")

    if "Effective SL" not in s:
        effective_line = "        f'Effective SL    : {_fmt_float(risk_exec.get(\"effective_stop_loss\") or protective.get(\"active_stop_loss\") or risk_plan.get(\"stop_loss\"), 4)}',\n"
        markers = [
            "        f'Risk exec       : {risk_exec.get(\"status\") or (\"READY\" if risk_exec.get(\"ready\") else \"-\")} / {risk_exec.get(\"exit_signal\") or (\"HOLD\" if not risk_exec.get(\"exit_required\") else risk_exec.get(\"exit_action\")) or \"-\"}',\n",
            "        f'Risk exit       : {risk_exec.get(\"exit_action\") or \"NONE\"} / {risk_exec.get(\"exit_reason\") or protective.get(\"last_exit_reason\") or \"-\"}',\n",
            "        f'Partial TP      : {_fmt_float(protective.get(\"partial_tp_price\"), 4)} / {_fmt_pct(protective.get(\"partial_tp_close_pct\"))} / hit {bool(protective.get(\"partial_tp_triggered\") or risk_exec.get(\"partial_tp_triggered\"))}',\n",
        ]
        for marker in markers:
            if marker in s:
                s = s.replace(marker, effective_line + marker, 1)
                changes.append("dashboard.effective_sl_line")
                break
        else:
            raise RuntimeError("Dashboard position management insertion marker not found for Effective SL")

    # Make Partial TP line accept the legacy partial_tp_done alias in addition to partial_tp_triggered.
    if "risk_exec.get(\"partial_tp_done\")" not in s and "risk_exec.get('partial_tp_done')" not in s:
        s = s.replace(
            "protective.get(\"partial_tp_triggered\") or risk_exec.get(\"partial_tp_triggered\")",
            "protective.get(\"partial_tp_triggered\") or risk_exec.get(\"partial_tp_triggered\") or risk_exec.get(\"partial_tp_done\")",
        )
        s = s.replace(
            "protective.get('partial_tp_triggered') or risk_exec.get('partial_tp_triggered')",
            "protective.get('partial_tp_triggered') or risk_exec.get('partial_tp_triggered') or risk_exec.get('partial_tp_done')",
        )
        changes.append("dashboard.partial_tp_done_alias")

    write(path, s)
    return changes


def main() -> None:
    all_changes: list[str] = []
    for fn in (patch_models, patch_engine, patch_dashboard):
        all_changes.extend(fn())
    print("4B.4.3.6.6.11c hotfix applied")
    if all_changes:
        for item in all_changes:
            print(f" - {item}")
    else:
        print(" - no changes needed")


if __name__ == "__main__":
    main()
