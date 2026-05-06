from __future__ import annotations

from types import SimpleNamespace

from tradebot.config import Settings
from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Position, RiskPlan, RuntimeState, SymbolRules
from tradebot.ui.dashboard import build_position_management_text
from tradebot.utils import utc_ms


class DummyStore:
    def __init__(self) -> None:
        self.data = {}

    def set_json(self, key: str, value: dict) -> None:
        self.data[key] = value

    def fetch_logs(self, limit: int = 80, order: str = "asc") -> list[dict]:
        return []


class DummyLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict | None = None, **_: object) -> None:
        self.events.append(("INFO", code, data or {}))

    def warn(self, code: str, message: str, data: dict | None = None, **_: object) -> None:
        self.events.append(("WARN", code, data or {}))


def make_engine(*, mark: float = 100.0, qty: float = 1.0, risk_plan: RiskPlan | None = None) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = Settings(auto_trade_on_signal=True)
    engine.store = DummyStore()
    engine.logger = DummyLogger()
    engine.symbol_rules = SymbolRules(
        symbol="ETHUSDT",
        base_asset="ETH",
        quote_asset="USDT",
        tick_size=0.01,
        step_size=0.0001,
        min_qty=0.0001,
        max_qty=10_000,
        min_notional=5.0,
    )
    engine.runtime = RuntimeState(symbol="ETHUSDT")
    engine.runtime.balances = {"ETH": Balance(free=qty, dust=0.0), "USDT": Balance(free=1000.0)}
    engine.runtime.position = Position(qty=qty, entry_price=100.0, source="test", opened_at=utc_ms(), risk_plan=risk_plan)
    engine.runtime.pending = None
    engine._latest_book = {"bestBid": mark, "bestAsk": mark + 0.1}
    engine._closed_candles = [SimpleNamespace(close=mark, high=mark, low=mark, open=mark) for _ in range(20)]
    engine._running = True
    return engine


def test_stop_loss_hit_triggers_full_exit_snapshot() -> None:
    risk = RiskPlan(entry_price=100.0, stop_loss=95.0, take_profit=120.0)
    engine = make_engine(mark=94.0, risk_plan=risk)

    snapshot = engine._risk_plan_execution_snapshot(engine.runtime.position, 94.0, mutate=True)

    assert snapshot["status"] == "TRIGGERED"
    assert snapshot["exit_signal"] == "FULL_EXIT"
    assert snapshot["exit_reason"] == "STOP_LOSS_HIT"
    assert snapshot["should_submit_exit"] is True
    assert snapshot["suggested_exit_qty"] == 1.0


def test_break_even_moves_effective_stop_without_exit() -> None:
    risk = RiskPlan(
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=130.0,
        break_even_trigger_price=105.0,
        break_even_stop_price=100.02,
    )
    engine = make_engine(mark=106.0, risk_plan=risk)

    snapshot = engine._risk_plan_execution_snapshot(engine.runtime.position, 106.0, mutate=True)

    assert snapshot["exit_signal"] == "HOLD"
    assert snapshot["break_even_armed"] is True
    assert snapshot["effective_stop_loss"] == 100.02
    assert risk.break_even_moved is True


def test_trailing_stop_updates_after_break_even_when_allowed() -> None:
    risk = RiskPlan(
        atr=2.0,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=130.0,
        break_even_trigger_price=102.0,
        break_even_stop_price=100.02,
        trailing_enabled=True,
    )
    engine = make_engine(mark=110.0, risk_plan=risk)
    engine.settings.trailing_only_after_break_even = False
    engine.settings.trailing_atr_multiplier = 1.0

    snapshot = engine._risk_plan_execution_snapshot(engine.runtime.position, 110.0, mutate=True)

    assert snapshot["trailing_armed"] is True
    assert snapshot["trailing_stop"] == 108.0
    assert snapshot["effective_stop_loss"] == 108.0


def test_partial_take_profit_suggests_partial_exit_qty() -> None:
    risk = RiskPlan(
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=130.0,
        partial_tp_price=110.0,
        partial_tp_close_pct=50.0,
    )
    engine = make_engine(mark=111.0, qty=2.0, risk_plan=risk)

    snapshot = engine._risk_plan_execution_snapshot(engine.runtime.position, 111.0, mutate=True)

    assert snapshot["exit_signal"] == "PARTIAL_EXIT"
    assert snapshot["exit_reason"] == "PARTIAL_TP_HIT"
    assert snapshot["suggested_exit_qty"] == 1.0
    assert snapshot["suggested_close_pct"] == 50.0


def test_time_stop_has_priority_before_take_profit() -> None:
    risk = RiskPlan(entry_price=100.0, stop_loss=95.0, take_profit=105.0)
    engine = make_engine(mark=106.0, risk_plan=risk)
    engine.settings.position_max_hold_sec = 1
    engine.runtime.position.opened_at = utc_ms() - 10_000

    snapshot = engine._risk_plan_execution_snapshot(engine.runtime.position, 106.0, mutate=True)

    assert snapshot["exit_signal"] == "FULL_EXIT"
    assert snapshot["exit_reason"] == "TIME_STOP_HIT"


def test_dashboard_position_text_includes_risk_execution_contract() -> None:
    status = {
        "position_snapshot": {
            "present": True,
            "qty": 1.0,
            "entry_price": 100.0,
            "mark_price": 101.0,
            "unrealized_pnl": 1.0,
            "unrealized_pnl_pct": 1.0,
            "source": "test",
            "risk_plan": {"stop_loss": 95.0, "take_profit": 120.0},
            "protective_exit": {"protective_exit_ready": True, "tradable_exit_qty": 1.0, "exit_notional": 101.0},
            "risk_execution": {
                "status": "READY",
                "exit_signal": "HOLD",
                "effective_stop_loss": 95.0,
                "trailing_stop": None,
                "break_even_armed": False,
                "partial_tp_done": False,
                "position_max_hold_sec": 0,
            },
        }
    }

    text = build_position_management_text(status)

    assert "Risk exec       : READY / HOLD" in text
    assert "Effective SL" in text
    assert "Partial TP done" in text
