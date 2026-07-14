def test_phase62f_contract_report_ready():
    from tradebot.full_repo_regression_stabilization_62F import build_phase62f_report
    r=build_phase62f_report()
    assert r['ok'] is True
    assert r['contract_ready_count']==r['contract_count']
    for key in ('paper_submit_enabled_by_patch','network_order_submit_performed','approved_for_live_real','approved_for_exchange_submit','exchange_submit_performed'):
        assert r[key] is False
