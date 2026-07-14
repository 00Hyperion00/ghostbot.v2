from __future__ import annotations

from pathlib import Path

from tradebot.release_audit_legacy_api_drift_compatibility_h7 import build_phase61_h7_report

ROOT = Path(__file__).resolve().parents[1]


def test_phase61_h7_report_ready() -> None:
    report = build_phase61_h7_report(project_root=ROOT)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["phase_61_h7_closed"] is True
    assert report["legacy_api_contract_ready_count"] == report["legacy_api_contract_count"]
    assert report["runtime_lock_handle_export_present"] is True
    assert report["runtime_lock_handle_object_ok"] is True
    assert report["final_safety_violation_count"] == 0


def test_phase61_h7_runtime_lock_handle_import_and_mapping_behavior() -> None:
    from tradebot.production_hardening import RuntimeLockHandle, acquire_runtime_lock, release_runtime_lock

    handle = acquire_runtime_lock(project_root=ROOT)
    assert isinstance(handle, RuntimeLockHandle)
    assert isinstance(handle, dict)
    assert handle["ok"] is True
    assert handle["runtime_start_performed"] is False
    assert handle["network_order_submit_performed"] is False
    assert callable(handle.release)
    released = release_runtime_lock(handle)
    assert isinstance(released, RuntimeLockHandle)
    assert released["runtime_lock_released"] is True


def test_phase61_h7_production_snapshot_preserves_prior_keys() -> None:
    from tradebot.production_hardening import build_production_hardening_snapshot

    snapshot = build_production_hardening_snapshot(project_root=ROOT)
    for key in (
        "production_hardening_signature_compatibility_v2",
        "production_hardening_signature_compatibility_h3",
        "production_hardening_signature_compatibility_h4",
        "production_hardening_signature_compatibility_h5",
        "production_hardening_signature_compatibility_h6",
        "production_hardening_signature_compatibility_h7",
        "runtime_lock_handle_export_compatibility_h7",
    ):
        assert snapshot[key] is True
    assert snapshot["paper_submit_enabled_by_patch"] is False
    assert snapshot["exchange_submit_performed"] is False
    assert snapshot["approved_for_live_real"] is False


def test_phase61_h7_orchestrator_import_boundary() -> None:
    import tradebot.cockpit.orchestrator  # noqa: F401


def test_phase61_h7_safety_locks_false() -> None:
    report = build_phase61_h7_report(project_root=ROOT)
    for key in (
        "paper_submit_enabled_by_patch",
        "paper_submit_performed",
        "paper_order_submit_performed",
        "network_order_submit_performed",
        "network_request_performed",
        "approved_for_live_real",
        "approved_for_exchange_submit",
        "exchange_submit_performed",
        "private_api_access_allowed",
        "runtime_start_performed",
        "training_performed",
        "reload_performed",
    ):
        assert report[key] is False
