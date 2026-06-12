from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.binance_environment import (  # noqa: E402
    BINANCE_ENVIRONMENT_ROUTER_VERSION,
    BinanceEnvironmentError,
    binance_environment_snapshot,
    build_combined_market_stream_url,
    resolve_binance_environment,
)
from tradebot.config import Settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Binance REST / WebSocket environment consistency audit")
    parser.add_argument("--config", type=Path, default=Path("config.local.yaml"))
    parser.add_argument("--market-type")
    parser.add_argument("--base-url")
    parser.add_argument("--symbol")
    parser.add_argument("--interval")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_yaml(args.config) if args.config.exists() else Settings()
    market_type = args.market_type or settings.market_type
    base_url = args.base_url or settings.base_url
    symbol = args.symbol or settings.symbol
    interval = args.interval or settings.kline_interval
    try:
        profile = resolve_binance_environment(market_type, base_url)
        snapshot = binance_environment_snapshot(profile, configured_rest_base_url=base_url)
        snapshot["market_ws_url"] = build_combined_market_stream_url(profile, symbol=symbol, kline_interval=interval)
        snapshot["ok"] = True
        exit_code = 0
    except BinanceEnvironmentError as error:
        snapshot = error.to_snapshot()
        snapshot["ok"] = False
        exit_code = 1
    snapshot.update(
        {
            "contract_version": BINANCE_ENVIRONMENT_ROUTER_VERSION,
            "read_only": True,
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "trading_action_performed": False,
        }
    )
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
