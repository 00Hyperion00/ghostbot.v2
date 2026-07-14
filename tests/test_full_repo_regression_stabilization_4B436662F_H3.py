from pathlib import Path

def test_62f_h3_hyp006_syntax_and_phase61_restore_contracts() -> None:
    import py_compile
    py_compile.compile("src/tradebot/hyp006_shadow_registration_operator_approval.py", doraise=True)
    from tradebot.hyp006_shadow_registration_operator_approval import build_registration_script
    script = build_registration_script(project_root=Path("Masaüstü/trade_botV2"), approval_json=Path("approval.json"), reports_dir=Path("reports/hyp006_r1_canonical"), symbols=["ADAUSDT"])
    assert "hyp006_scheduler_stdout.log" in script
    assert "--registration-json" in script
    from tradebot.production_hardening import acquire_runtime_lock, build_production_hardening_snapshot, release_runtime_lock
    snapshot = build_production_hardening_snapshot(project_root=Path.cwd())
    assert snapshot["project_root"] == str(Path.cwd().resolve())
    assert snapshot["paper_order_submit_performed"] is False
    assert snapshot["production_hardening_signature_compatibility_v2"] is True
    handle = acquire_runtime_lock(project_root=Path.cwd())
    assert handle["ok"] is True
    release_runtime_lock(handle)
    assert handle["released"] is True
    from tradebot.operator_cockpit_v2_read_only import OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION, _build_risk_sizing_in_memory_evidence_pack
    assert OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION == "4B.4.3.6.6.27G"
    assert "61-H4" in OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION
    assert isinstance(_build_risk_sizing_in_memory_evidence_pack(), dict)
    assert isinstance(_build_risk_sizing_in_memory_evidence_pack(Path.cwd()), dict)
