from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33j_h1_operator_identity_signature_fixed() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "operator_id = require_operator_identity(context)" not in text
    assert 'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.create_plan")' in text
    assert 'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.confirm_plan")' in text
    assert 'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.verify_completion")' in text
    assert 'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.create_from_reviewed_candidate")' in text
    assert 'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.confirm_manual_external_recovery")' in text
    assert 'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.verify_no_mismatch")' in text


def test_33j_h1_routes_still_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/recovery-plan-apply/create-from-reviewed-candidate" in text
    assert "/api/cockpit/recovery-plan-apply/confirm-manual-external-recovery" in text
    assert "/api/cockpit/recovery-plan-apply/verify-no-mismatch" in text
    assert "CONFIRM_CREATE_RECOVERY_PLAN_FROM_REVIEWED_CANDIDATE" in (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")


def test_33j_h1_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633J_H1.py"), doraise=True)
