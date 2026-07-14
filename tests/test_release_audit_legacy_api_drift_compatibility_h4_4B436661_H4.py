from __future__ import annotations

from pathlib import Path

from tradebot.release_audit_legacy_api_drift_compatibility_h4 import build_phase61_h4_report

ROOT = Path(__file__).resolve().parents[1]


def test_phase61_h4_report_ready() -> None:
    report = build_phase61_h4_report(project_root=ROOT)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["phase_61_h4_closed"] is True
    assert report["legacy_api_contract_ready_count"] == report["legacy_api_contract_count"]
    assert report["production_hardening_import_path_resolved"] is True
    assert report["production_hardening_signature_compatibility_v2_preserved"] is True
    assert report["production_hardening_signature_compatibility_h3_preserved"] is True
    assert report["operator_cockpit_telemetry_version_export_present"] is True
    assert report["final_safety_violation_count"] == 0


def test_phase61_h4_production_hardening_snapshot_preserves_h2_h3_keys() -> None:
    from tradebot.production_hardening import build_production_hardening_snapshot
    snapshot = build_production_hardening_snapshot(project_root=ROOT)
    assert snapshot["ok"] is True
    assert snapshot["project_root"] == str(ROOT.resolve())
    assert snapshot["production_hardening_signature_compatibility_v2"] is True
    assert snapshot["production_hardening_signature_compatibility_h3"] is True
    assert snapshot["production_hardening_signature_compatibility_h4"] is True
    assert snapshot["paper_submit_enabled_by_patch"] is False
    assert snapshot["paper_order_submit_performed"] is False
    assert snapshot["network_order_submit_performed"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["exchange_submit_performed"] is False
    assert snapshot["private_api_access_allowed"] is False


def test_phase61_h4_cockpit_telemetry_version_export() -> None:
    from tradebot.operator_cockpit_v2_read_only import (
        OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY,
        OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED,
        OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY,
        OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION,
    )
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, str)
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED, str)
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY, str)
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION, str)
    assert "61-H4" in OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION


def test_phase61_h4_detected_test_import_symbols_are_exported() -> None:
    report = build_phase61_h4_report(project_root=ROOT)
    missing = [item for item in report["legacy_api_contracts"] if not item["restored_by_patch"]]
    assert missing == []


def test_phase61_h4_safety_locks_false() -> None:
    report = build_phase61_h4_report(project_root=ROOT)
    for key in ("paper_submit_enabled_by_patch", "paper_submit_performed", "paper_order_submit_performed", "network_order_submit_performed", "network_request_performed", "approved_for_live_real", "live_real_approved_by_patch", "approved_for_exchange_submit", "exchange_submit_performed", "private_api_access_allowed", "runtime_start_performed", "training_performed", "reload_performed"):
        assert report[key] is False
