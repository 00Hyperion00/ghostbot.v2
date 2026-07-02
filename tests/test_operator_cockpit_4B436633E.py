from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33e_contract_markers_present() -> None:
    schemas = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION" in schemas
    assert "4B.4.3.6.6.33E" in schemas


def test_33e_runtime_lock_diagnostic_and_clear_contract_present() -> None:
    orch = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "inspect_runtime_lock" in orch
    assert "duplicate_instance_blocked" in orch
    assert "stale_reclaim_safe" in orch
    assert "clear_stale_runtime_lock" in orch
    assert "CONFIRM_CLEAR_STALE_RUNTIME_LOCK" in orch
    assert "RUNTIME_LOCK_CLEAR_NOT_SAFE" in orch


def test_33e_red_risk_entry_guard_present_and_restrictive_only() -> None:
    orch = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_entry_guard_visibility" in orch
    assert "RED_RISK_BADGE_ENTRY_GUARD" in orch
    assert "force_buy_disabled" in orch
    assert "order_path_mutation" not in orch.lower()
    assert "live_real_enablement" not in orch.lower()


def test_33e_app_routes_and_audit_outcomes_present() -> None:
    app = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/operator-actions" in app
    assert "/api/cockpit/runtime-lock/clear-stale" in app
    assert "BLOCKED_ENTRY_GUARD" in app
    assert "runtime_lock.clear_stale" in app


def test_33e_security_confirmation_contract_present() -> None:
    security = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"runtime_lock.clear_stale": "CONFIRM_CLEAR_STALE_RUNTIME_LOCK"' in security
    assert "AUTH_TOKEN_CONFIGURED" in security


def test_33e_ui_panels_and_button_guards_present() -> None:
    html = (_root() / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    css = (_root() / "src/tradebot/cockpit/static/styles.css").read_text(encoding="utf-8")
    assert "Runtime Lock" in html
    assert "Entry Guard" in html
    assert "Action Audit Summary" in html
    assert "Clear Stale Lock" in html
    assert "renderRuntimeLock" in js
    assert "renderEntryGuard" in js
    assert "renderActionAuditSummary" in js
    assert "applyProtectedButtonGuards" in js
    assert "ACTION_AUDIT_RUNTIME_LOCK_VERSION" in js
    assert "4B.4.3.6.6.33E" in css


def test_33e_python_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
