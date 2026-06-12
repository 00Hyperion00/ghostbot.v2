from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tradebot.binance_environment import (
    BINANCE_ENVIRONMENT_FAIL_CLOSED,
    BINANCE_ENVIRONMENT_ROUTER_VERSION,
    BinanceEnvironmentError,
    build_combined_market_stream_url,
    resolve_binance_environment,
)
from tradebot.config import Settings
from tradebot.config_safety import build_config_safety_snapshot
from tradebot.exchange.binance import BinanceSpotClient


def test_27a_declares_fail_closed_router_contract() -> None:
    assert BINANCE_ENVIRONMENT_ROUTER_VERSION == "4B.4.3.6.6.27A"
    assert BINANCE_ENVIRONMENT_FAIL_CLOSED is True


@pytest.mark.parametrize(
    ("market_type", "base_url", "expected_ws_host"),
    [
        ("spot_demo", "https://demo-api.binance.com", "demo-stream.binance.com"),
        ("spot_testnet", "https://testnet.binance.vision", "stream.testnet.binance.vision"),
        ("spot_mainnet", "https://api.binance.com", "stream.binance.com"),
    ],
)
def test_27a_routes_rest_and_ws_to_same_environment(market_type: str, base_url: str, expected_ws_host: str) -> None:
    profile = resolve_binance_environment(market_type, base_url)
    url = build_combined_market_stream_url(profile, symbol="ETHUSDT", kline_interval="4h")
    assert expected_ws_host in url
    assert "ethusdt@bookTicker/ethusdt@miniTicker/ethusdt@kline_4h" in url


def test_27a_blocks_demo_profile_with_mainnet_rest_host() -> None:
    with pytest.raises(BinanceEnvironmentError, match="BINANCE_REST_WS_ENVIRONMENT_MISMATCH"):
        resolve_binance_environment("spot_demo", "https://api.binance.com")


def test_27a_blocks_rest_base_url_with_api_path_to_prevent_double_api_path() -> None:
    with pytest.raises(BinanceEnvironmentError, match="BINANCE_REST_BASE_URL_INVALID"):
        resolve_binance_environment("spot_demo", "https://demo-api.binance.com/api")


def test_27a_binance_client_uses_demo_ws_router() -> None:
    client = BinanceSpotClient.__new__(BinanceSpotClient)
    client.settings = Settings(market_type="spot_demo", base_url="https://demo-api.binance.com", symbol="SOLUSDT", kline_interval="1m")
    client.base_url = client.settings.base_url
    client.endpoint_profile = resolve_binance_environment(client.settings.market_type, client.base_url)
    assert client._market_ws_url().startswith("wss://demo-stream.binance.com:9443/stream?streams=solusdt@bookTicker")


def test_27a_config_safety_fails_closed_on_environment_mismatch() -> None:
    snapshot = build_config_safety_snapshot(Settings(market_type="spot_demo", base_url="https://api.binance.com", ai_provider_enabled=False))
    assert snapshot["severity"] == "critical"
    assert snapshot["safe_to_trade"] is False
    assert "BINANCE_REST_WS_ENVIRONMENT_MISMATCH" in snapshot["reason_codes"]
    assert snapshot["binance_environment"]["ok"] is False


def test_27a_config_safety_exposes_valid_demo_market_stream_route() -> None:
    snapshot = build_config_safety_snapshot(Settings(market_type="spot_demo", base_url="https://demo-api.binance.com", ai_provider_enabled=False))
    assert snapshot["binance_environment"]["ok"] is True
    assert snapshot["binance_environment"]["market_stream_base_url"] == "wss://demo-stream.binance.com:9443/stream"


def test_27a_checker_reports_fail_closed_mismatch(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    config = tmp_path / "config.yaml"
    config.write_text("market_type: spot_demo\nbase_url: https://api.binance.com\n", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(root / "tools/check_binance_environment_router_4B436627A.py"), "--config", str(config), "--once-json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["reason_code"] == "BINANCE_REST_WS_ENVIRONMENT_MISMATCH"
    assert payload["trading_action_performed"] is False
