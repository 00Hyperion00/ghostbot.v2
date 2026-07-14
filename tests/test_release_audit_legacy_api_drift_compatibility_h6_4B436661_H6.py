from __future__ import annotations

from pathlib import Path

from tradebot.release_audit_legacy_api_drift_compatibility_h6 import build_phase61_h6_report

ROOT = Path(__file__).resolve().parents[1]


def test_phase61_h6_report_ready() -> None:
    report = build_phase61_h6_report(project_root=ROOT)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["phase_61_h6_closed"] is True
    assert report["legacy_api_contract_ready_count"] == report["legacy_api_contract_count"]
    assert report["legacy_api_callable_failures"] == []
    assert report["production_hardening_unknown_location_closed"] is True
    assert report["operator_cockpit_risk_sizing_evidence_pack_callable_fixed_by_h6"] is True
    assert report["final_safety_violation_count"] == 0


def test_phase61_h6_production_hardening_import_and_snapshot() -> None:
    import tradebot.production_hardening as ph
    from tradebot.production_hardening import acquire_runtime_lock, build_production_hardening_snapshot, canonical_evidence_commit_decision, evaluate_promotion_gate, release_runtime_lock
    assert getattr(ph, "__file__", None) or getattr(ph, "__path__", None)
    snapshot = build_production_hardening_snapshot(project_root=ROOT)
    assert snapshot["ok"] is True
    assert snapshot["project_root"] == str(ROOT.resolve())
    for key in (
        "production_hardening_signature_compatibility_v2",
        "production_hardening_signature_compatibility_h3",
        "production_hardening_signature_compatibility_h4",
        "production_hardening_import_finalization_h5",
        "production_hardening_import_finalization_h6",
    ):
        assert snapshot[key] is True
    for key in ("paper_submit_enabled_by_patch", "paper_order_submit_performed", "network_order_submit_performed", "network_request_performed", "approved_for_live_real", "exchange_submit_performed", "private_api_access_allowed"):
        assert snapshot[key] is False
    for fn in (acquire_runtime_lock, canonical_evidence_commit_decision, evaluate_promotion_gate, release_runtime_lock):
        assert callable(fn)


def test_phase61_h6_operator_cockpit_public_contracts_are_callable() -> None:
    from tradebot.operator_cockpit_v2_read_only import DASHBOARD_HTML, OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED, OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY, OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION, _build_in_memory_evidence_pack, _build_risk_sizing_in_memory_evidence_pack, _safe_action_manifest, collect_operator_cockpit_snapshot, make_operator_cockpit_server
    assert isinstance(DASHBOARD_HTML, str)
    for value in (OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED, OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY, OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION):
        assert isinstance(value, str)
    for fn in (_build_in_memory_evidence_pack, _build_risk_sizing_in_memory_evidence_pack, _safe_action_manifest, collect_operator_cockpit_snapshot, make_operator_cockpit_server):
        assert callable(fn)
    pack = _build_risk_sizing_in_memory_evidence_pack()
    assert isinstance(pack, dict)
    assert pack["paper_submit_enabled_by_patch"] is False
    assert pack["exchange_submit_performed"] is False


def test_phase61_h6_h4_h5_alias_reports_ready() -> None:
    from tradebot.release_audit_legacy_api_drift_compatibility_h4 import build_phase61_h4_report
    from tradebot.release_audit_legacy_api_drift_compatibility_h5 import build_phase61_h5_report
    h4 = build_phase61_h4_report(project_root=ROOT)
    h5 = build_phase61_h5_report(project_root=ROOT)
    assert h4["ok"] is True
    assert h4["phase_61_h4_closed"] is True
    assert h5["ok"] is True
    assert h5["phase_61_h5_closed"] is True
    assert [item for item in h4["legacy_api_contracts"] if not item["restored_by_patch"]] == []
    assert [item for item in h5["legacy_api_contracts"] if not item["restored_by_patch"]] == []


def test_phase61_h6_safety_locks_false() -> None:
    report = build_phase61_h6_report(project_root=ROOT)
    for key in ("paper_submit_enabled_by_patch", "paper_submit_performed", "paper_order_submit_performed", "network_order_submit_performed", "network_request_performed", "approved_for_live_real", "live_real_approved_by_patch", "approved_for_exchange_submit", "exchange_submit_performed", "private_api_access_allowed", "runtime_start_performed", "training_performed", "reload_performed"):
        assert report[key] is False
