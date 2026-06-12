from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Candle, RuntimeState, SymbolRules
from tradebot.position_sizing import (
    STABLE_ENTRY_SKIP_CODE_COMPAT_VERSION,
    stable_entry_skip_code_for_sizing_error,
)


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[str, str, dict]] = []
        self.warn_calls: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.info_calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data))

    def error(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data))


class MissingPreflightExchange:
    def __init__(self) -> None:
        self.create_calls = 0

    async def create_limit_order(self, **kwargs):
        self.create_calls += 1
        return {"status": "NEW", "orderId": "unexpected"}


class RaisingPreflightExchange(MissingPreflightExchange):
    async def run_entry_order_preflight(self, **kwargs):
        raise RuntimeError("adapter failed")


@dataclass
class DummySettings:
    symbol: str = "ETHUSDT"
    execution_mode: str = "live_demo"
    order_notional_usd: float = 25.0
    sizing_mode: str = "fixed_quote"
    risk_percent_quote_balance: float = 2.5
    quote_balance_reserve_usd: float = 0.0
    max_quote_budget_usd: float = 0.0
    min_notional_buffer_multiplier: float = 1.10
    auto_trade_cooldown_sec: int = 5
    max_daily_trades: int = 0
    max_consecutive_losses: int = 3
    max_daily_loss_pct: float = 2.0
    safe_mode_cooldown_min: int = 60
    force_entry_price_mode: str = "passive"


async def _noop(*args, **kwargs):
    return None


def make_engine(exchange) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = exchange
    engine.runtime = RuntimeState(state="FLAT", ws_status="CONNECTED", symbol="ETHUSDT")
    engine.runtime.session.day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    engine.runtime.balances = {
        "USDT": Balance(free=100.0, locked=0.0, dust=0.0),
        "ETH": Balance(free=0.0, locked=0.0, dust=0.0),
    }
    engine.symbol_rules = SymbolRules(
        symbol="ETHUSDT",
        base_asset="ETH",
        quote_asset="USDT",
        tick_size=0.01,
        step_size=0.0001,
        min_qty=0.0001,
        max_qty=100000.0,
        min_notional=5.0,
    )
    engine._closed_candles = [Candle(open_time=1, close_time=2, open=2500.0, high=2501.0, low=2499.0, close=2500.0, volume=1.0, quote_volume=2500.0)]
    engine._latest_book = {"bestBid": 2500.0, "bestAsk": 2500.1}
    engine._save_runtime = lambda: None
    engine.sync_balances = _noop
    engine._submit_lock = None
    return engine


def test_27f_h1_skip_code_contract_is_stable_and_internal_reason_is_not_lost() -> None:
    assert STABLE_ENTRY_SKIP_CODE_COMPAT_VERSION == "4B.4.3.6.6.27F-H1"
    assert stable_entry_skip_code_for_sizing_error("SIZING_QUOTE_BUDGET_BELOW_MIN_NOTIONAL") == "MIN_NOTIONAL_BLOCKED"
    assert stable_entry_skip_code_for_sizing_error("SIZING_USABLE_QUOTE_BALANCE_NON_POSITIVE") == "INSUFFICIENT_QUOTE_BALANCE"
    assert stable_entry_skip_code_for_sizing_error("SIZING_REFERENCE_PRICE_NON_POSITIVE") == "ENTRY_SIZING_BLOCKED"


@pytest.mark.asyncio
async def test_27f_h1_low_quote_balance_uses_stable_skip_code_and_preserves_internal_diagnostic() -> None:
    engine = make_engine(MissingPreflightExchange())
    engine.runtime.balances["USDT"] = Balance(free=1.0, locked=0.0, dust=0.0)

    await TradeBotEngine._submit_entry(engine, source="manual_force_buy")

    assert engine.exchange.create_calls == 0
    warning = next(call for call in engine.logger.warn_calls if call[0] == "ENTRY_BLOCKED")
    assert warning[2]["skipCode"] == "MIN_NOTIONAL_BLOCKED"
    assert warning[2]["sizingReasonCode"] == "SIZING_QUOTE_BUDGET_BELOW_MIN_NOTIONAL"


@pytest.mark.asyncio
async def test_27f_h1_missing_entry_preflight_adapter_blocks_without_order_or_exception() -> None:
    engine = make_engine(MissingPreflightExchange())

    await TradeBotEngine._submit_entry(engine, source="manual_force_buy")

    assert engine.exchange.create_calls == 0
    assert engine.runtime.pending is None
    warning = next(call for call in engine.logger.warn_calls if call[0] == "LIVE_PREFLIGHT_BLOCKED")
    assert warning[2]["reasonCode"] == "PREFLIGHT_ADAPTER_UNAVAILABLE"
    assert warning[2]["tradingActionPerformed"] is False
    assert engine.runtime.last_preflight.startswith("BLOCKED | ENTRY | PREFLIGHT_ADAPTER_UNAVAILABLE")


@pytest.mark.asyncio
async def test_27f_h1_unexpected_entry_preflight_adapter_failure_blocks_without_order_or_exception() -> None:
    engine = make_engine(RaisingPreflightExchange())

    await TradeBotEngine._submit_entry(engine, source="manual_force_buy")

    assert engine.exchange.create_calls == 0
    assert engine.runtime.pending is None
    warning = next(call for call in engine.logger.warn_calls if call[0] == "LIVE_PREFLIGHT_BLOCKED")
    assert warning[2]["reasonCode"] == "PREFLIGHT_ADAPTER_CALL_FAILED"
    assert warning[2]["causeReasonCode"] == "RuntimeError"
    assert warning[2]["tradingActionPerformed"] is False
