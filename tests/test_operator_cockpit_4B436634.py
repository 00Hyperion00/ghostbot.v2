from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_34_schema_version_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION" in text
    assert "4B.4.3.6.6.34" in text


def test_34_orchestrator_demo_entry_gate_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_demo_entry_execution_gate_snapshot" in text
    assert "demo_entry_dry_run" in text
    assert "verify_demo_entry_filters" in text
    assert "record_demo_entry_intent" in text
    assert "authorize_demo_only_entry" in text
    assert "verify_post_entry_protective_exit" in text


def test_34_fail_closed_reason_codes_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "DEMO_SPOT_LIVE_DEMO_RUNTIME_CONFIRMED" in text
    assert "ENTRY_ACTION_DRY_RUN_REQUIRED" in text
    assert "ENTRY_MIN_NOTIONAL_NOT_SATISFIED" in text
    assert "DEMO_ONLY_TRADE_AUTHORIZATION_REQUIRED" in text
    assert "POST_ENTRY_PROTECTIVE_EXIT_NOT_VERIFIED" in text
    assert "DEMO_ENTRY_EXECUTION_GATE_NOT_READY" in text


def test_34_routes_and_confirmations_present() -> None:
    app_text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    sec_text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert "/api/cockpit/demo-entry-execution-gate" in app_text
    assert "/api/cockpit/demo-entry/dry-run" in app_text
    assert "/api/cockpit/demo-entry/authorize-demo-only-entry" in app_text
    assert "CONFIRM_DEMO_ENTRY_DRY_RUN" in sec_text
    assert "CONFIRM_AUTHORIZE_DEMO_ONLY_ENTRY" in sec_text
    assert "CONFIRM_VERIFY_POST_ENTRY_PROTECTIVE_EXIT" in sec_text


def test_34_force_buy_requires_demo_gate() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "demo_trade_enablement_ready" in text
    assert "Force BUY blocked by 34 demo entry execution gate" in text
    assert "Force BUY requested through 34 demo-only controlled entry gate" in text


def test_34_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436634.py"), doraise=True)
    py_compile.compile(str(_root() / "tools/compile_operator_cockpit_4B436634.py"), doraise=True)
