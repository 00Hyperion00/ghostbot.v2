from __future__ import annotations

from types import SimpleNamespace

from tradebot.engine import TradeBotEngine
from tradebot.models import PendingOrder, Position, RuntimeState
from tradebot.performance import (
    PerformanceConfig,
    append_trade,
    close_trade_record,
    new_entry_record,
    summarize_event_codes,
    summarize_performance,
    update_open_trade_on_partial_exit,
)


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls = []

    def info(self, code: str, message: str, data: dict, **kwargs) -> None:
        self.info_calls.append((code, message, data))


class DummyStore:
    def fetch_logs(self, **kwargs):
        return [
            {'code': 'AUTO_TRADE_SKIP'},
            {'code': 'AUTO_ENTRY_BLOCKED'},
            {'code': 'RISK_EXIT_TRIGGERED'},
        ]


def test_performance_summary_calculates_win_loss_and_profit_factor() -> None:
    trades = [
        {'realized_pnl': 2.0, 'hold_time_sec': 30, 'result': 'WIN'},
        {'realized_pnl': -1.0, 'hold_time_sec': 60, 'result': 'LOSS'},
        {'realized_pnl': 0.0, 'hold_time_sec': 90, 'result': 'BREAKEVEN'},
    ]

    snapshot = summarize_performance(
        trades=trades,
        open_trade=None,
        config=PerformanceConfig(window_size=20),
        symbol='ETHUSDT',
        logs=[],
    )

    assert snapshot['contract_version'] == '4B.4.3.6.6.14'
    assert snapshot['closed_trade_count'] == 3
    assert snapshot['realized_pnl'] == 1.0
    assert snapshot['win_count'] == 1
    assert snapshot['loss_count'] == 1
    assert snapshot['breakeven_count'] == 1
    assert snapshot['win_rate_pct'] == 33.33
    assert snapshot['profit_factor'] == 2.0
    assert snapshot['avg_hold_time_sec'] == 60.0


def test_entry_partial_exit_and_close_trade_records_are_compatible() -> None:
    open_trade = new_entry_record(
        symbol='ETHUSDT',
        entry_price=100.0,
        qty=1.0,
        source='manual_force_buy',
        order_id='entry-1',
        client_order_id='client-1',
        entry_at=1_000,
    )

    open_trade = update_open_trade_on_partial_exit(
        open_trade,
        exit_price=105.0,
        exit_qty=0.4,
        pnl=2.0,
        remaining_qty=0.6,
        exit_at=11_000,
    )

    closed = close_trade_record(
        open_trade,
        symbol='ETHUSDT',
        entry_price=100.0,
        qty=1.0,
        exit_price=110.0,
        exit_qty=0.6,
        pnl=6.0,
        exit_source='manual_force_sell',
        fill_source='unit_test',
        exit_at=21_000,
    )

    assert open_trade is not None
    assert open_trade['partial_exit_count'] == 1
    assert open_trade['partial_realized_pnl'] == 2.0
    assert closed['status'] == 'CLOSED'
    assert closed['realized_pnl'] == 8.0
    assert closed['realized_pnl_pct'] == 8.0
    assert closed['result'] == 'WIN'
    assert closed['hold_time_sec'] == 20
    assert closed['partial_exit_count'] == 1


def test_append_trade_respects_window_size() -> None:
    trades = []
    for idx in range(5):
        trades = append_trade(trades, {'id': idx, 'realized_pnl': idx}, window_size=3)

    assert [trade['id'] for trade in trades] == [2, 3, 4]


def test_event_code_summary_tracks_guard_and_risk_counts() -> None:
    counts = summarize_event_codes([
        {'code': 'AUTO_TRADE_SKIP'},
        {'code': 'AUTO_TRADE_SKIP'},
        {'code': 'AUTO_EXIT_BLOCKED'},
        {'code': 'RISK_EXIT_TRIGGERED'},
        {'code': 'ORDER_CANCELED'},
    ])

    assert counts['auto_trade_skip'] == 2
    assert counts['auto_exit_blocked'] == 1
    assert counts['risk_exit_triggered'] == 1
    assert counts['order_canceled'] == 1


def test_engine_status_includes_performance_snapshot() -> None:
    engine = TradeBotEngine.__new__(TradeBotEngine)
    engine.settings = SimpleNamespace(
        symbol='ETHUSDT',
        performance_analytics_enabled=True,
        performance_analytics_window_size=20,
        performance_breakeven_epsilon=1e-9,
    )
    engine.runtime = RuntimeState()
    engine.runtime.performance_trades = [{'realized_pnl': 1.25, 'hold_time_sec': 45}]
    engine.runtime.performance_open_trade = None
    engine.store = DummyStore()

    snapshot = TradeBotEngine._performance_snapshot(engine)

    assert snapshot['contract_version'] == '4B.4.3.6.6.14'
    assert snapshot['closed_trade_count'] == 1
    assert snapshot['realized_pnl'] == 1.25
    assert snapshot['guard_counts']['auto_trade_skip'] == 1
    assert snapshot['guard_counts']['auto_entry_blocked'] == 1
    assert snapshot['guard_counts']['risk_exit_triggered'] == 1


def test_engine_records_entry_and_full_exit_performance() -> None:
    engine = TradeBotEngine.__new__(TradeBotEngine)
    engine.settings = SimpleNamespace(
        symbol='ETHUSDT',
        performance_analytics_enabled=True,
        performance_analytics_window_size=20,
        performance_breakeven_epsilon=1e-9,
    )
    engine.runtime = RuntimeState()
    engine.store = DummyStore()
    engine.logger = DummyLogger()
    pending_buy = PendingOrder(side='BUY', price=100.0, qty=1.0, order_id='buy-1', client_order_id='cbuy-1', source='manual_force_buy')
    pending_sell = PendingOrder(side='SELL', price=110.0, qty=1.0, order_id='sell-1', client_order_id='csell-1', source='manual_force_sell')
    position = Position(qty=1.0, entry_price=100.0, source='manual_force_buy', order_id='buy-1')

    TradeBotEngine._record_performance_entry(engine, pending_buy, fill_price=100.0, fill_qty=1.0, source='unit_test')
    TradeBotEngine._record_performance_exit(engine, position, pending_sell, fill_price=110.0, fill_qty=1.0, pnl=10.0, remaining_qty=0.0, source='unit_test', closed=True)

    assert engine.runtime.performance_open_trade is None
    assert len(engine.runtime.performance_trades) == 1
    assert engine.runtime.performance_trades[0]['realized_pnl'] == 10.0
    assert engine.runtime.performance_trades[0]['result'] == 'WIN'
    assert engine.runtime.performance_snapshot['closed_trade_count'] == 1
    assert any(call[0] == 'PERFORMANCE_TRADE_CLOSED' for call in engine.logger.info_calls)
