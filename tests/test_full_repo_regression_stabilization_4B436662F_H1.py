from __future__ import annotations
from pathlib import Path


def test_62f_h1_phase61_constants_and_hyp005_exports() -> None:
    from tradebot.hyp005_shadow_evidence_path_contract import HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION, write_json_ascii_atomic
    from tradebot.operator_cockpit_v2_read_only import OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY
    from tradebot.release_audit_legacy_api_drift_compatibility_h7 import build_phase61_h7_report

    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY, str)
    assert isinstance(OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY, str)
    assert HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION == "4B.4.3.6.6.27G-H2"
    assert build_phase61_h7_report(project_root=Path.cwd())["runtime_lock_handle_object_ok"] is True
    assert callable(write_json_ascii_atomic)
