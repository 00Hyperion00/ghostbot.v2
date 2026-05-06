from tradebot.ui.dashboard import extract_signal_markers, filter_logs, format_log_line


def test_filter_logs_respects_search_symbol_and_code() -> None:
    logs = [
        {'ts': 1, 'level': 'INFO', 'code': 'STRATEGY_EVAL', 'message': 'foo', 'data': {'symbol': 'ETHUSDT'}},
        {'ts': 2, 'level': 'WARN', 'code': 'ORDER_FILLED', 'message': 'bar', 'data': {'symbol': 'BTCUSDT', 'side': 'SELL'}},
    ]
    assert len(filter_logs(logs, symbol_filter='ETHUSDT')) == 1
    assert len(filter_logs(logs, code_filter='ORDER')) == 1
    assert len(filter_logs(logs, search='bar')) == 1
    assert 'STRATEGY_EVAL' in format_log_line(logs[0])


def test_extract_signal_markers_maps_runtime_events_to_nearest_candles() -> None:
    candles = [
        {'close_time': 1000, 'close': 10.0},
        {'close_time': 2000, 'close': 11.0},
        {'close_time': 3000, 'close': 12.0},
    ]
    logs = [
        {'ts': 1900, 'code': 'STRATEGY_EVAL', 'data': {'signal': 'BUY'}},
        {'ts': 3100, 'code': 'ORDER_FILLED', 'data': {'side': 'SELL'}},
        {'ts': 900, 'code': 'AUTO_SIGNAL_EFFECTIVE', 'data': {'effectiveSignal': 'HOLD'}},
    ]
    markers = extract_signal_markers(logs, candles)
    assert markers['BUY'] == [(1, 11.0)]
    assert markers['SELL'] == [(2, 12.0)]
    assert markers['HOLD'] == [(0, 10.0)]
