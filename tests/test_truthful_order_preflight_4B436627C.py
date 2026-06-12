from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tradebot.config import Settings
from tradebot.enums import ExecutionMode, MarketType
from tradebot.exchange.binance import BinanceSpotClient
from tradebot.order_preflight import (
    ENTRY_NEW_RISK_PREFLIGHT_FAIL_CLOSED,
    RISK_REDUCING_EXIT_PREFLIGHT_NOT_FABRICATED,
    TRUTHFUL_OPEN_ORDERS_VERIFICATION,
    TRUTHFUL_ORDER_PREFLIGHT_VERSION,
    TRUTHFUL_ORDER_TEST_VERIFICATION,
    OrderPreflightError,
    blocked_entry_preflight_snapshot,
    risk_reducing_exit_preflight_snapshot,
    successful_entry_preflight_snapshot,
)


def _settings(
    *,
    execution_mode: str = ExecutionMode.LIVE_DEMO.value,
    market_type: str = MarketType.SPOT_DEMO.value,
    base_url: str = "https://demo-api.binance.com",
    armed: bool = False,
    double_confirm: bool = False,
) -> Settings:
    return Settings(
        market_type=market_type,
        base_url=base_url,
        execution_mode=execution_mode,
        live_trading_armed=armed,
        live_real_double_confirm=double_confirm,
        symbol="ETHUSDT",
        kline_interval="1m",
    )


def _run(coro):
    return asyncio.run(coro)


def test_27c_declares_truthful_fail_closed_contract() -> None:
    assert TRUTHFUL_ORDER_PREFLIGHT_VERSION == "4B.4.3.6.6.27C"
    assert TRUTHFUL_OPEN_ORDERS_VERIFICATION is True
    assert TRUTHFUL_ORDER_TEST_VERIFICATION is True
    assert ENTRY_NEW_RISK_PREFLIGHT_FAIL_CLOSED is True
    assert RISK_REDUCING_EXIT_PREFLIGHT_NOT_FABRICATED is True


def test_27c_success_snapshot_records_real_checks() -> None:
    payload = successful_entry_preflight_snapshot(symbol="ETHUSDT", open_orders_count=0).to_log_payload()
    assert payload["ok"] is True
    assert payload["openOrdersCheckPerformed"] is True
    assert payload["openOrdersCount"] == 0
    assert payload["orderTestPerformed"] is True
    assert payload["orderTestOk"] is True
    assert payload["tradingActionPerformed"] is False


def test_27c_exit_snapshot_never_fabricates_entry_checks() -> None:
    payload = risk_reducing_exit_preflight_snapshot(symbol="ETHUSDT").to_log_payload()
    assert payload["ok"] is True
    assert payload["action"] == "EXIT_RISK_REDUCING"
    assert payload["openOrdersCheckPerformed"] is False
    assert payload["openOrdersCount"] is None
    assert payload["orderTestPerformed"] is False
    assert payload["orderTestOk"] is None


def test_27c_blocked_snapshot_preserves_unknown_as_null() -> None:
    payload = blocked_entry_preflight_snapshot(
        symbol="ETHUSDT",
        reason_code="PREFLIGHT_OPEN_ORDERS_QUERY_FAILED",
        message="query failed",
        open_orders_check_performed=False,
        open_orders_count=None,
        order_test_performed=False,
        order_test_ok=None,
    ).to_log_payload()
    assert payload["ok"] is False
    assert payload["openOrdersCount"] is None
    assert payload["orderTestOk"] is None


def test_27c_exchange_success_calls_policy_then_open_orders_then_order_test(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BinanceSpotClient(_settings())
    events: list[str] = []

    original_policy = client._enforce_signed_request_policy

    def policy(method: str, path: str, params: dict | None = None) -> None:
        events.append(f"policy:{method}:{path}")
        original_policy(method, path, params)

    async def fetch_open_orders(symbol: str | None = None):
        events.append(f"openOrders:{symbol}")
        return []

    async def create_limit_order(**kwargs):
        events.append(f"orderTest:{kwargs.get('test')}")
        assert kwargs["test"] is True
        return {}

    monkeypatch.setattr(client, "_enforce_signed_request_policy", policy)
    monkeypatch.setattr(client, "fetch_open_orders", fetch_open_orders)
    monkeypatch.setattr(client, "create_limit_order", create_limit_order)
    try:
        payload = _run(client.run_entry_order_preflight(symbol="ETHUSDT", quantity=0.1, price=1000.0, client_order_id="TEST-1"))
    finally:
        _run(client.close())
    assert events == ["policy:POST:/api/v3/order", "openOrders:ETHUSDT", "orderTest:True"]
    assert payload["ok"] is True
    assert payload["openOrdersCount"] == 0


def test_27c_existing_open_orders_blocks_before_order_test(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BinanceSpotClient(_settings())
    called = {"order_test": False}

    async def fetch_open_orders(symbol: str | None = None):
        return [{"orderId": 1}]

    async def create_limit_order(**kwargs):
        called["order_test"] = True
        return {}

    monkeypatch.setattr(client, "fetch_open_orders", fetch_open_orders)
    monkeypatch.setattr(client, "create_limit_order", create_limit_order)
    try:
        with pytest.raises(OrderPreflightError) as exc:
            _run(client.run_entry_order_preflight(symbol="ETHUSDT", quantity=0.1, price=1000.0, client_order_id="TEST-2"))
    finally:
        _run(client.close())
    assert exc.value.code == "PREFLIGHT_EXISTING_OPEN_ORDERS_BLOCKED"
    payload = exc.value.to_log_payload()
    assert payload["openOrdersCheckPerformed"] is True
    assert payload["openOrdersCount"] == 1
    assert payload["orderTestPerformed"] is False
    assert payload["orderTestOk"] is None
    assert called["order_test"] is False


def test_27c_open_orders_query_failure_denies_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BinanceSpotClient(_settings())

    async def fetch_open_orders(symbol: str | None = None):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(client, "fetch_open_orders", fetch_open_orders)
    try:
        with pytest.raises(OrderPreflightError) as exc:
            _run(client.run_entry_order_preflight(symbol="ETHUSDT", quantity=0.1, price=1000.0, client_order_id="TEST-3"))
    finally:
        _run(client.close())
    assert exc.value.code == "PREFLIGHT_OPEN_ORDERS_QUERY_FAILED"
    payload = exc.value.to_log_payload()
    assert payload["openOrdersCheckPerformed"] is False
    assert payload["openOrdersCount"] is None
    assert payload["orderTestPerformed"] is False
    assert payload["orderTestOk"] is None


def test_27c_order_test_failure_denies_entry_truthfully(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BinanceSpotClient(_settings())

    async def fetch_open_orders(symbol: str | None = None):
        return []

    async def create_limit_order(**kwargs):
        raise RuntimeError("order-test rejected")

    monkeypatch.setattr(client, "fetch_open_orders", fetch_open_orders)
    monkeypatch.setattr(client, "create_limit_order", create_limit_order)
    try:
        with pytest.raises(OrderPreflightError) as exc:
            _run(client.run_entry_order_preflight(symbol="ETHUSDT", quantity=0.1, price=1000.0, client_order_id="TEST-4"))
    finally:
        _run(client.close())
    assert exc.value.code == "PREFLIGHT_ORDER_TEST_FAILED"
    payload = exc.value.to_log_payload()
    assert payload["openOrdersCheckPerformed"] is True
    assert payload["openOrdersCount"] == 0
    assert payload["orderTestPerformed"] is True
    assert payload["orderTestOk"] is False


def test_27c_dry_run_policy_blocks_before_any_network(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BinanceSpotClient(_settings(execution_mode=ExecutionMode.DRY_RUN.value))
    called = {"network": False}

    async def fetch_open_orders(symbol: str | None = None):
        called["network"] = True
        return []

    monkeypatch.setattr(client, "fetch_open_orders", fetch_open_orders)
    try:
        with pytest.raises(OrderPreflightError) as exc:
            _run(client.run_entry_order_preflight(symbol="ETHUSDT", quantity=0.1, price=1000.0, client_order_id="TEST-5"))
    finally:
        _run(client.close())
    assert exc.value.code == "PREFLIGHT_EXECUTION_POLICY_BLOCKED"
    assert exc.value.cause_reason_code == "EXECUTION_POLICY_DRY_RUN_ORDER_BLOCKED"
    assert called["network"] is False


def test_27c_engine_source_has_truthful_wiring_and_no_fabricated_literals() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "src/tradebot/engine.py").read_text(encoding="utf-8")
    assert "await self.exchange.run_entry_order_preflight(" in text
    assert "risk_reducing_exit_preflight_snapshot" in text
    assert "'openOrdersCount': 0,'orderTestOk': True" not in text


def test_27c_checker_is_read_only_and_blocks_failed_scenario() -> None:
    root = Path(__file__).resolve().parents[1]
    checker = root / "tools/check_truthful_order_preflight_4B436627C.py"
    ok_run = subprocess.run(
        [sys.executable, str(checker), "--scenario", "successful_entry", "--once-json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ok_run.returncode == 0, ok_run.stderr
    ok_payload = json.loads(ok_run.stdout)
    assert ok_payload["ok"] is True
    assert ok_payload["read_only"] is True
    assert ok_payload["network_request_performed"] is False
    assert ok_payload["trading_action_performed"] is False

    blocked_run = subprocess.run(
        [sys.executable, str(checker), "--scenario", "existing_open_orders", "--once-json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert blocked_run.returncode == 1
    blocked_payload = json.loads(blocked_run.stdout)
    assert blocked_payload["ok"] is False
    assert blocked_payload["snapshot"]["reasonCode"] == "PREFLIGHT_EXISTING_OPEN_ORDERS_BLOCKED"
    assert blocked_payload["trading_action_performed"] is False
