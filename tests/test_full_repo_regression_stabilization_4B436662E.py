
def test_phase62e_contract_report_ready():
    from tradebot.full_repo_regression_stabilization_62E import build_phase62e_report
    report = build_phase62e_report()
    assert report["ok"] is True
    assert report["contract_ready_count"] == report["contract_count"]
    for key in ("paper_submit_enabled_by_patch", "network_order_submit_performed", "approved_for_live_real", "approved_for_exchange_submit", "exchange_submit_performed"):
        assert report[key] is False
