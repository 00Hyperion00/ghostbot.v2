from __future__ import annotations

import py_compile
from pathlib import Path

def _root() -> Path:
    return Path(__file__).resolve().parents[1]

def test_33f_contract_markers_present() -> None:
    schemas = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION" in schemas
    assert "4B.4.3.6.6.33F" in schemas

def test_33f_reconciliation_snapshot_and_entry_block_present() -> None:
    orch = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_risk_reconciliation_snapshot" in orch
    assert "build_balance_review_snapshot" in orch
    assert "ENTRY_BLOCK_UNTIL_RECONCILED" in orch
    assert "always_on_entry_guard_snapshot" in orch
    assert "manual_acknowledgement_allows_entry" in orch and "False" in orch

def test_33f_manual_ack_gate_is_restrictive_only() -> None:
    orch = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "entry_remains_blocked_until_reconciled" in orch
    assert "acknowledgement_allows_entry" in orch
    assert "live_real_enablement" not in orch.lower()
    assert "order_path_mutation" not in orch.lower()

def test_33f_app_routes_present() -> None:
    app = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/risk-reconciliation" in app
    assert "/api/cockpit/risk-reconciliation/acknowledge" in app
    assert "/api/cockpit/risk-reconciliation/clear-acknowledgement" in app

def test_33f_security_confirmation_contract_present() -> None:
    security = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"risk_reconciliation.acknowledge": "CONFIRM_ACKNOWLEDGE_POSITION_NOT_TRACKED"' in security
    assert '"risk_reconciliation.clear_acknowledgement": "CONFIRM_CLEAR_RECONCILIATION_ACKNOWLEDGEMENT"' in security

def test_33f_ui_reconcile_wizard_present() -> None:
    html = (_root() / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    css = (_root() / "src/tradebot/cockpit/static/styles.css").read_text(encoding="utf-8")
    assert "Risk Reconciliation" in html
    assert "Read-Only Balance Review" in html
    assert "renderRiskReconciliation" in js
    assert "renderBalanceReview" in js
    assert "CONFIRM_ACKNOWLEDGE_POSITION_NOT_TRACKED" in js
    assert "4B.4.3.6.6.33F" in css

def test_33f_python_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
