def test_phase62f_h2_smoke():
    from tradebot.full_repo_regression_stabilization_62F_H2 import build_phase62f_h2_snapshot
    p=build_phase62f_h2_snapshot(); assert p['paper_submit_performed'] is False; assert p['approved_for_live_real'] is False
