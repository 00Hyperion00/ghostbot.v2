
from __future__ import annotations

from pathlib import Path

from tradebot.release_audit_legacy_api_drift_compatibility_h3 import build_phase61_h3_report

ROOT = Path(__file__).resolve().parents[1]


def test_phase61_h3_report_ready() -> None:
    report = build_phase61_h3_report(project_root=ROOT)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["phase_61_h3_closed"] is True
    assert report["legacy_api_contract_ready_count"] == report["legacy_api_contract_count"]
    assert report["production_hardening_import_path_resolved"] is True
    assert report["operator_cockpit_runtime_telemetry_export_present"] is True
    assert report["final_safety_violation_count"] == 0


def test_phase61_h3_production_hardening_import_path_and_signature() -> None:
    from tradebot.production_hardening import build_production_hardening_snapshot

    snapshot = build_production_hardening_snapshot(project_root=ROOT)
    assert isinstance(snapshot, dict)
    assert snapshot["ok"] is True
    assert snapshot["paper_submit_enabled_by_patch"] is False
    assert snapshot["exchange_submit_performed"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["project_root"] == str(ROOT.resolve())


def test_phase61_h3_operator_cockpit_runtime_telemetry_export() -> None:
    from tradebot.operator_cockpit_v2_read_only import (
        OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY,
        OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED,
        OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY,
    )

    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY, str)
    assert "RUNTIME_TELEMETRY" in OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, str)
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED, str)


def test_phase61_h3_safety_locks_false() -> None:
    report = build_phase61_h3_report(project_root=ROOT)
    for key in (
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
        "training_performed",
        "reload_performed",
    ):
        assert report[key] is False
