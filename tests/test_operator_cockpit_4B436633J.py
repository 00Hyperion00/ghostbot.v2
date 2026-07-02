from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33j_schema_contract_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION" in text
    assert "4B.4.3.6.6.33J" in text


def test_33j_security_confirmations_present() -> None:
    text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"recovery_plan_apply.create_from_reviewed_candidate": "CONFIRM_CREATE_RECOVERY_PLAN_FROM_REVIEWED_CANDIDATE"' in text
    assert '"recovery_plan_apply.confirm_manual_external_recovery": "CONFIRM_CONFIRM_MANUAL_EXTERNAL_RECOVERY_PLAN"' in text
    assert '"recovery_plan_apply.verify_no_mismatch": "CONFIRM_VERIFY_RECOVERY_NO_MISMATCH"' in text
    assert '"recovery_plan_apply.clear": "CONFIRM_CLEAR_RECOVERY_PLAN_APPLY"' in text


def test_33j_orchestrator_fail_closed_verification_gate_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "create_recovery_plan_from_reviewed_candidate" in text
    assert "confirm_manual_external_recovery_plan" in text
    assert "verify_recovery_no_mismatch" in text
    assert "entry_guard_release_only_after_verified_no_mismatch" in text
    assert "verified_no_mismatch" in text
    assert "auto_position_mutation_performed" in text
    assert "engine_position_state_mutated" in text
    assert "live_real_enablement" not in text.lower()
    assert "order_path_mutation" not in text.lower()


def test_33j_routes_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/recovery-plan-apply-verification-gate" in text
    assert "/api/cockpit/recovery-plan-apply/create-from-reviewed-candidate" in text
    assert "/api/cockpit/recovery-plan-apply/confirm-manual-external-recovery" in text
    assert "/api/cockpit/recovery-plan-apply/verify-no-mismatch" in text
    assert "/api/cockpit/recovery-plan-apply/clear" in text


def test_33j_runtime_helper_present() -> None:
    helper = (_root() / "tools/check_cockpit_runtime_4B436633J.py").read_text(encoding="utf-8")
    assert "recovery_plan_apply_verification_gate" in helper
    assert "verified_no_mismatch" in helper
    assert "entry_guard_release_verified" in helper


def test_33j_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633J.py"), doraise=True)
