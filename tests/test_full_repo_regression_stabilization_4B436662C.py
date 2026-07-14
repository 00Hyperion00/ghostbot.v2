from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_62c_phase61_constants_keep_dual_legacy_contracts() -> None:
    from tradebot.operator_cockpit_v2_read_only import (
        OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY,
        OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY,
        OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION,
    )
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, str)
    assert "RISK_SIZING_AUDIT_PARITY" in OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY
    assert OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION == "4B.4.3.6.6.27G"
    assert "61-H4" in OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION
    assert "RUNTIME_TELEMETRY" in OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY


def test_62c_production_hardening_snapshot_restores_prior_keys() -> None:
    from tradebot.production_hardening import RuntimeLockHandle, acquire_runtime_lock, build_production_hardening_snapshot, release_runtime_lock
    snapshot = build_production_hardening_snapshot(project_root=ROOT)
    for key in (
        "private_api_access_allowed",
        "production_hardening_import_finalization_h5",
        "production_hardening_import_finalization_h6",
        "production_hardening_import_finalization_h7",
        "runtime_lock_handle_export_compatibility_h7",
    ):
        assert key in snapshot
    assert snapshot["private_api_access_allowed"] is False
    handle = acquire_runtime_lock(project_root=ROOT)
    assert isinstance(handle, RuntimeLockHandle)
    assert isinstance(handle, dict)
    assert release_runtime_lock(handle)["runtime_lock_released"] is True


def test_62c_hyp005_utf8_collection_exports_are_present(tmp_path: Path) -> None:
    from tradebot.hyp005_shadow_evidence_path_contract import (
        HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION,
        resolve_evidence_output_directory,
        resolve_existing_evidence_path,
        write_json_ascii_atomic,
    )
    assert HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION == "4B.4.3.6.6.27G-H2"
    target = tmp_path / "Masaüstü" / "x.json"
    target.parent.mkdir(parents=True)
    write_json_ascii_atomic(target, {"ok": True})
    assert resolve_existing_evidence_path(target, field="x", expect_directory=False) == target.resolve()
    out = resolve_evidence_output_directory(tmp_path / "Masaüstü" / "out", field="out_dir")
    assert out.exists()


def test_62c_risk_sizing_pack_no_arg_is_dict() -> None:
    from tradebot.operator_cockpit_v2_read_only import _build_risk_sizing_in_memory_evidence_pack
    assert isinstance(_build_risk_sizing_in_memory_evidence_pack(), dict)
