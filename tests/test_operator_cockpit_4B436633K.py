from __future__ import annotations

import py_compile
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_33k_schema_version_present() -> None:
    text = (_root() / "src/tradebot/cockpit/schemas.py").read_text(encoding="utf-8")
    assert "OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION" in text
    assert "4B.4.3.6.6.33K" in text


def test_33k_security_confirmations_present() -> None:
    text = (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")
    assert '"external_recovery_evidence.capture": "CONFIRM_CAPTURE_EXTERNAL_RECOVERY_EVIDENCE"' in text
    assert '"external_recovery_evidence.capture_post_recovery_snapshot": "CONFIRM_CAPTURE_POST_RECOVERY_BALANCE_SNAPSHOT"' in text
    assert '"external_recovery_evidence.no_mismatch_preflight": "CONFIRM_RUN_EXTERNAL_RECOVERY_NO_MISMATCH_PREFLIGHT"' in text
    assert '"external_recovery_evidence.verify_no_mismatch_safe_apply": "CONFIRM_VERIFY_RECOVERY_NO_MISMATCH_WITH_EVIDENCE"' in text


def test_33k_orchestrator_fail_closed_evidence_gate_present() -> None:
    text = (_root() / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    assert "build_external_recovery_evidence_gate_snapshot" in text
    assert "capture_external_recovery_evidence" in text
    assert "capture_post_recovery_balance_snapshot" in text
    assert "run_external_recovery_no_mismatch_preflight" in text
    assert "verify_no_mismatch_safe_apply_with_evidence" in text
    assert "ENTRY_GUARD_REMAINS_BLOCKED_UNTIL_EVIDENCE_AND_FRESH_NO_MISMATCH" in text
    assert "EXTERNAL_RECOVERY_EVIDENCE_NOT_VERIFIED" in text
    assert "auto_position_mutation_performed" in text
    assert "engine_position_state_mutated" in text


def test_33k_routes_present() -> None:
    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    assert "/api/cockpit/external-recovery-evidence-gate" in text
    assert "/api/cockpit/external-recovery-evidence/capture" in text
    assert "/api/cockpit/external-recovery-evidence/capture-post-recovery-snapshot" in text
    assert "/api/cockpit/external-recovery-evidence/no-mismatch-preflight" in text
    assert "/api/cockpit/external-recovery-evidence/verify-no-mismatch-safe-apply" in text


def test_33k_runtime_helper_present() -> None:
    helper = (_root() / "tools/check_cockpit_runtime_4B436633K.py").read_text(encoding="utf-8")
    assert "external_recovery_evidence_gate" in helper
    assert "verified_no_mismatch_with_evidence" in helper
    assert "post_recovery_snapshot_fresh" in helper


def test_33k_compile_contract() -> None:
    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):
        py_compile.compile(str(file_path), doraise=True)
    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633K.py"), doraise=True)
