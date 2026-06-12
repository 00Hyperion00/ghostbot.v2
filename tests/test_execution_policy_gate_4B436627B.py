from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tradebot.binance_environment import resolve_binance_environment
from tradebot.config import Settings
from tradebot.enums import ExecutionMode, MarketType
from tradebot.exchange.binance import BinanceSpotClient
from tradebot.execution_policy import (
    EXECUTION_POLICY_GATE_VERSION,
    ExecutionPolicyAction,
    ExecutionPolicyError,
    build_execution_policy_snapshot,
    classify_limit_order_action,
    enforce_execution_policy,
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


def _profile(settings: Settings):
    return resolve_binance_environment(settings.market_type, settings.base_url)


def test_27b_declares_exchange_level_fail_closed_policy() -> None:
    assert EXECUTION_POLICY_GATE_VERSION == "4B.4.3.6.6.27B"
    assert classify_limit_order_action(side="BUY") == ExecutionPolicyAction.ENTRY_NEW_RISK.value
    assert classify_limit_order_action(side="SELL") == ExecutionPolicyAction.EXIT_RISK_REDUCING.value
    assert classify_limit_order_action(side="BUY", test=True) == ExecutionPolicyAction.ORDER_TEST.value
    assert classify_limit_order_action(side="BROKEN") == "UNKNOWN_LIMIT_ORDER_ACTION"


def test_27b_live_demo_allows_demo_entry_exit_cancel_and_order_test() -> None:
    settings = _settings()
    profile = _profile(settings)
    for action in (
        ExecutionPolicyAction.ENTRY_NEW_RISK.value,
        ExecutionPolicyAction.EXIT_RISK_REDUCING.value,
        ExecutionPolicyAction.CANCEL_PENDING.value,
        ExecutionPolicyAction.ORDER_TEST.value,
    ):
        decision = enforce_execution_policy(settings, profile, action=action)
        assert decision.allowed is True
        assert decision.reason_code == "EXECUTION_POLICY_LIVE_DEMO_ALLOWED"


def test_27b_dry_run_blocks_all_signed_order_actions() -> None:
    settings = _settings(execution_mode=ExecutionMode.DRY_RUN.value)
    profile = _profile(settings)
    for action in (
        ExecutionPolicyAction.ENTRY_NEW_RISK.value,
        ExecutionPolicyAction.EXIT_RISK_REDUCING.value,
        ExecutionPolicyAction.CANCEL_PENDING.value,
        ExecutionPolicyAction.ORDER_TEST.value,
    ):
        with pytest.raises(ExecutionPolicyError) as exc:
            enforce_execution_policy(settings, profile, action=action)
        assert exc.value.code == "EXECUTION_POLICY_DRY_RUN_ORDER_BLOCKED"


def test_27b_live_real_entry_requires_armed_and_double_confirm() -> None:
    settings = _settings(
        execution_mode=ExecutionMode.LIVE_REAL.value,
        market_type=MarketType.SPOT_MAINNET.value,
        base_url="https://api.binance.com",
        armed=False,
        double_confirm=False,
    )
    profile = _profile(settings)
    with pytest.raises(ExecutionPolicyError) as exc:
        enforce_execution_policy(settings, profile, action=ExecutionPolicyAction.ENTRY_NEW_RISK.value)
    assert exc.value.code == "EXECUTION_POLICY_LIVE_REAL_NOT_ARMED"

    settings = _settings(
        execution_mode=ExecutionMode.LIVE_REAL.value,
        market_type=MarketType.SPOT_MAINNET.value,
        base_url="https://api.binance.com",
        armed=True,
        double_confirm=False,
    )
    profile = _profile(settings)
    with pytest.raises(ExecutionPolicyError) as exc2:
        enforce_execution_policy(settings, profile, action=ExecutionPolicyAction.ENTRY_NEW_RISK.value)
    assert exc2.value.code == "EXECUTION_POLICY_LIVE_REAL_DOUBLE_CONFIRM_MISSING"

    settings = _settings(
        execution_mode=ExecutionMode.LIVE_REAL.value,
        market_type=MarketType.SPOT_MAINNET.value,
        base_url="https://api.binance.com",
        armed=True,
        double_confirm=True,
    )
    profile = _profile(settings)
    decision = enforce_execution_policy(settings, profile, action=ExecutionPolicyAction.ENTRY_NEW_RISK.value)
    assert decision.allowed is True
    assert decision.reason_code == "EXECUTION_POLICY_LIVE_REAL_NEW_RISK_ALLOWED"


def test_27b_live_real_risk_reducing_exit_and_cancel_are_not_trapped_by_armed_flags() -> None:
    settings = _settings(
        execution_mode=ExecutionMode.LIVE_REAL.value,
        market_type=MarketType.SPOT_MAINNET.value,
        base_url="https://api.binance.com",
        armed=False,
        double_confirm=False,
    )
    profile = _profile(settings)
    for action in (ExecutionPolicyAction.EXIT_RISK_REDUCING.value, ExecutionPolicyAction.CANCEL_PENDING.value):
        decision = enforce_execution_policy(settings, profile, action=action)
        assert decision.allowed is True
        assert decision.risk_reducing is True
        assert decision.reason_code == "EXECUTION_POLICY_LIVE_REAL_RISK_REDUCING_ALLOWED"


def test_27b_live_real_rejects_non_mainnet_environment() -> None:
    settings = _settings(
        execution_mode=ExecutionMode.LIVE_REAL.value,
        market_type=MarketType.SPOT_DEMO.value,
        base_url="https://demo-api.binance.com",
        armed=True,
        double_confirm=True,
    )
    profile = _profile(settings)
    with pytest.raises(ExecutionPolicyError) as exc:
        enforce_execution_policy(settings, profile, action=ExecutionPolicyAction.ENTRY_NEW_RISK.value)
    assert exc.value.code == "EXECUTION_POLICY_LIVE_REAL_ENVIRONMENT_INVALID"


def test_27b_unknown_action_is_denied_by_default() -> None:
    settings = _settings()
    profile = _profile(settings)
    with pytest.raises(ExecutionPolicyError) as exc:
        enforce_execution_policy(settings, profile, action="SOMETHING_NEW")
    assert exc.value.code == "EXECUTION_POLICY_ACTION_CLASS_UNKNOWN"


def test_27b_binance_client_blocks_before_api_key_or_network() -> None:
    client = BinanceSpotClient(_settings(execution_mode=ExecutionMode.DRY_RUN.value))
    try:
        with pytest.raises(ExecutionPolicyError) as exc:
            client._enforce_signed_request_policy("POST", "/api/v3/order", {"side": "BUY"})
        assert exc.value.code == "EXECUTION_POLICY_DRY_RUN_ORDER_BLOCKED"
    finally:
        asyncio.run(client.close())


def test_27b_binance_client_classifies_cancel_and_unknown_signed_routes() -> None:
    client = BinanceSpotClient(_settings())
    try:
        assert client._signed_request_action("DELETE", "/api/v3/order", {}) == ExecutionPolicyAction.CANCEL_PENDING.value
        assert client._signed_request_action("PATCH", "/api/v3/order", {}) == "UNKNOWN_SIGNED_REQUEST_ACTION"
        with pytest.raises(ExecutionPolicyError) as exc:
            client._enforce_signed_request_policy("PATCH", "/api/v3/order", {})
        assert exc.value.code == "EXECUTION_POLICY_ACTION_CLASS_UNKNOWN"
    finally:
        asyncio.run(client.close())


def test_27b_snapshot_exposes_action_matrix() -> None:
    settings = _settings(execution_mode=ExecutionMode.DRY_RUN.value)
    snapshot = build_execution_policy_snapshot(settings, _profile(settings))
    assert snapshot["policy_version"] == "4B.4.3.6.6.27B"
    assert snapshot["entry_new_risk_allowed"] is False
    assert snapshot["risk_reducing_exit_allowed"] is False
    assert snapshot["cancel_pending_allowed"] is False
    assert snapshot["actions"]["ENTRY_NEW_RISK"]["reason_code"] == "EXECUTION_POLICY_DRY_RUN_ORDER_BLOCKED"


def test_27b_checker_is_read_only_and_returns_nonzero_for_blocked_action(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    checker = root / "tools" / "check_execution_policy_gate_4B436627B.py"
    ok_run = subprocess.run(
        [sys.executable, str(checker), "--market-type", "spot_demo", "--base-url", "https://demo-api.binance.com", "--execution-mode", "live_demo", "--action", "ENTRY_NEW_RISK", "--once-json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ok_run.returncode == 0, ok_run.stderr
    ok_payload = json.loads(ok_run.stdout)
    assert ok_payload["ok"] is True
    assert ok_payload["trading_action_performed"] is False

    blocked_run = subprocess.run(
        [sys.executable, str(checker), "--market-type", "spot_demo", "--base-url", "https://demo-api.binance.com", "--execution-mode", "dry_run", "--action", "ENTRY_NEW_RISK", "--once-json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert blocked_run.returncode == 1
    blocked_payload = json.loads(blocked_run.stdout)
    assert blocked_payload["ok"] is False
    assert blocked_payload["decision"]["reason_code"] == "EXECUTION_POLICY_DRY_RUN_ORDER_BLOCKED"
    assert blocked_payload["trading_action_performed"] is False
