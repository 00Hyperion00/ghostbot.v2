def test_62d_ready():
    from tradebot.full_repo_regression_stabilization_62D import build_phase62d_report
    assert build_phase62d_report()['ok'] is True
