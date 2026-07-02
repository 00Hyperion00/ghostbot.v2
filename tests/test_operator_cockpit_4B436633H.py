from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33h_schema_contract_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION" in text
    assert "4B.4.3.6.6.33H" in text


def test_33h_security_confirmations_present() -> None:
    text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"risk_reconciliation.apply_tracked_position_candidate_review": "CONFIRM_APPLY_TRACKED_POSITION_CANDIDATE_REVIEW"' in text
    assert '"risk_reconciliation.apply_dust_safe_clear": "CONFIRM_APPLY_DUST_SAFE_CLEAR"' in text
    assert '"runtime_lock.resolve_owner_mismatch": "CONFIRM_RESOLVE_RUNTIME_LOCK_OWNER_MISMATCH"' in text


def test_33h_orchestrator_apply_flow_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_reconciliation_decision_apply_snapshot" in text
    assert "build_runtime_lock_owner_mismatch_resolver" in text
    assert "apply_tracked_position_candidate_review" in text
    assert "apply_dust_safe_clear" in text
    assert "ENGINE_POSITION_STATE_NOT_MUTATED" in text
    assert "DUST_SAFE_CLEAR_REJECTED_NOT_ELIGIBLE" in text
    assert "live_real_enablement" not in text.lower()
    assert "order_path_mutation" not in text.lower()


def test_33h_routes_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/reconciliation-decision-apply" in text
    assert "/api/cockpit/risk-reconciliation/apply-tracked-position-candidate-review" in text
    assert "/api/cockpit/risk-reconciliation/apply-dust-safe-clear" in text
    assert "/api/cockpit/runtime-lock/resolve-owner-mismatch" in text


def test_33h_ui_and_helper_present() -> None:
    html = (_root() / "src/tradebot/cockpit/static/index.html").read_text(encoding="utf-8")
    js = (_root() / "src/tradebot/cockpit/static/app.js").read_text(encoding="utf-8")
    helper = (_root() / "tools/check_cockpit_runtime_4B436633H.py").read_text(encoding="utf-8")
    assert "Reconciliation Decision Apply" in html
    assert "renderReconciliationDecisionApply" in js
    assert "CONFIRM_APPLY_DUST_SAFE_CLEAR" in js
    assert "runtime_lock_owner_mismatch_resolver" in helper


def test_33h_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633H.py"), doraise=True)
