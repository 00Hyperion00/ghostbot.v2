
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_phase62a_report_ready():
    from tradebot.full_repo_regression_stabilization_62A import build_phase62a_report
    r=build_phase62a_report(ROOT); assert r['ok'] is True; assert r['final_safety_violation_count']==0
def test_phase62a_api_create_app_returns_app():
    from tradebot.api import create_app
    app=create_app(type('DummyEngine',(),{})()); assert app is not None and callable(app)
def test_phase62a_operator_exports_callable():
    from tradebot.operator_cockpit_v2_read_only import DASHBOARD_HTML,_build_in_memory_evidence_pack,_build_risk_sizing_in_memory_evidence_pack,make_operator_cockpit_server
    assert callable(_build_in_memory_evidence_pack); assert callable(_build_risk_sizing_in_memory_evidence_pack); assert callable(make_operator_cockpit_server); assert 'MAE / MFE verisi henüz oluşmadı.' in DASHBOARD_HTML
def test_phase62a_hyp005_contract_files_exist():
    assert (ROOT/'src/tradebot/hyp005_shadow_evidence_path_contract.py').exists(); assert (ROOT/'tools/_patch_payload/run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py').exists()
