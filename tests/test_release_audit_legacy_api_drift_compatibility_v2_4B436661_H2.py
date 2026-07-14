from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from tradebot.release_audit_legacy_api_drift_compatibility_v2 import (  # noqa: E402
    DECISION,
    build_legacy_api_drift_compatibility_v2_snapshot,
    verify_legacy_api_contracts,
)

def test_phase61_h2_snapshot_ready() -> None:
    snapshot = build_legacy_api_drift_compatibility_v2_snapshot(ROOT)
    assert snapshot["ok"] is True
    assert snapshot["status"] == "READY"
    assert snapshot["phase_61_h2_closed"] is True
    assert snapshot["decision"] == DECISION
    assert snapshot["legacy_api_contract_ready_count"] == 4
    assert snapshot["missing_legacy_api_contracts"] == []
    assert snapshot["legacy_api_callable_failures"] == []
    assert snapshot["production_hardening_project_root_signature_compatible"] is True
    assert snapshot["operator_cockpit_evidence_export_fail_closed_export_present"] is True

def test_phase61_h2_restores_production_hardening_project_root_signature() -> None:
    from tradebot.production_hardening import build_production_hardening_snapshot

    snapshot = build_production_hardening_snapshot(project_root=ROOT)
    assert isinstance(snapshot, dict)
    assert snapshot["ok"] is True
    assert snapshot["paper_submit_enabled_by_patch"] is False
    assert snapshot["paper_order_submit_performed"] is False
    assert snapshot["network_order_submit_performed"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["exchange_submit_performed"] is False
    assert snapshot["private_api_access_allowed"] is False
    assert snapshot["production_hardening_signature_compatibility_v2"] is True

def test_phase61_h2_restores_operator_cockpit_exports() -> None:
    from tradebot.operator_cockpit_v2_read_only import (
        OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY,
        OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED,
    )

    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, str)
    assert "RISK_SIZING_AUDIT_PARITY" in OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED, str)
    assert "EVIDENCE_EXPORT_FAIL_CLOSED" in OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED

def test_phase61_h2_contract_verifier() -> None:
    findings = verify_legacy_api_contracts(ROOT)
    assert len(findings) == 4
    assert all(item["module_imported"] for item in findings)
    assert all(item["symbol_present"] for item in findings)
    production = [item for item in findings if item["symbol"] == "build_production_hardening_snapshot"][0]
    assert production["callable_project_root_ok"] is True

def test_phase61_h2_safety_locks() -> None:
    snapshot = build_legacy_api_drift_compatibility_v2_snapshot(ROOT)
    locked = [
        "paper_submit_enabled_by_patch",
        "paper_submit_performed",
        "paper_order_submit_performed",
        "network_order_submit_performed",
        "network_request_performed",
        "approved_for_live_real",
        "live_real_approved_by_patch",
        "approved_for_exchange_submit",
        "exchange_submit_performed",
        "private_api_access_allowed",
        "runtime_start_performed",
        "runtime_start_command_executed",
        "training_performed",
        "reload_performed",
        "legacy_tests_skipped_by_patch",
    ]
    assert all(snapshot[key] is False for key in locked)
    assert snapshot["final_safety_violation_count"] == 0
    assert snapshot["next_phase_unlock_allowed"] is False
