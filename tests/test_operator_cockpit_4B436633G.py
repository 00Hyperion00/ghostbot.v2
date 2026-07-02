from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33g_schema_contract_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION" in text
    assert "4B.4.3.6.6.33G" in text


def test_33g_security_confirmations_present() -> None:
    text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"risk_reconciliation.confirm_balance_snapshot": "CONFIRM_BALANCE_SNAPSHOT_REVIEWED"' in text
    assert '"risk_reconciliation.resolve_dust_safe": "CONFIRM_RESOLVE_DUST_SAFE_BASE_BALANCE"' in text
    assert '"risk_reconciliation.adopt_position_candidate": "CONFIRM_ADOPT_TRACKED_POSITION_CANDIDATE"' in text


def test_33g_orchestrator_reconciliation_execution_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_reconciliation_execution_snapshot" in text
    assert "build_tracked_position_adoption_candidate" in text
    assert "entry_guard_release_only_after_reconciliation_clear" in text
    assert "adoption_mutates_engine_state" in text
    assert "ENGINE_POSITION_STATE_NOT_MUTATED" in text
    assert "live_real_enablement" not in text.lower()
    assert "order_path_mutation" not in text.lower()


def test_33g_routes_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/reconciliation-execution" in text
    assert "/api/cockpit/risk-reconciliation/confirm-balance-snapshot" in text
    assert "/api/cockpit/risk-reconciliation/resolve-dust-safe-base-balance" in text
    assert "/api/cockpit/risk-reconciliation/adopt-position-candidate" in text


def test_33g_ui_and_runtime_helper_present() -> None:
    html = (_root() / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    helper = (_root() / "tools/check_cockpit_runtime_4B436633G.py").read_text(encoding="utf-8")
    assert "Reconciliation Execution" in html
    assert "renderReconciliationExecution" in js
    assert "CONFIRM_BALANCE_SNAPSHOT_REVIEWED" in js
    assert "server_reachable" in helper


def test_33g_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633G.py"), doraise=True)
