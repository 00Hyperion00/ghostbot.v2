from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.order_preflight import (  # noqa: E402
    TRUTHFUL_ORDER_PREFLIGHT_VERSION,
    blocked_entry_preflight_snapshot,
    risk_reducing_exit_preflight_snapshot,
    successful_entry_preflight_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only truthful order-preflight contract checker")
    parser.add_argument(
        "--scenario",
        choices=["successful_entry", "existing_open_orders", "open_orders_query_failed", "order_test_failed", "risk_reducing_exit"],
        default="successful_entry",
    )
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    if args.scenario == "successful_entry":
        snapshot = successful_entry_preflight_snapshot(symbol=args.symbol, open_orders_count=0)
    elif args.scenario == "existing_open_orders":
        snapshot = blocked_entry_preflight_snapshot(
            symbol=args.symbol,
            reason_code="PREFLIGHT_EXISTING_OPEN_ORDERS_BLOCKED",
            message="Existing open orders detected; new-risk entry denied",
            open_orders_check_performed=True,
            open_orders_count=2,
            order_test_performed=False,
            order_test_ok=None,
        )
    elif args.scenario == "open_orders_query_failed":
        snapshot = blocked_entry_preflight_snapshot(
            symbol=args.symbol,
            reason_code="PREFLIGHT_OPEN_ORDERS_QUERY_FAILED",
            message="Open-orders query failed; new-risk entry denied",
            open_orders_check_performed=False,
            open_orders_count=None,
            order_test_performed=False,
            order_test_ok=None,
        )
    elif args.scenario == "order_test_failed":
        snapshot = blocked_entry_preflight_snapshot(
            symbol=args.symbol,
            reason_code="PREFLIGHT_ORDER_TEST_FAILED",
            message="Order-test request failed; new-risk entry denied",
            open_orders_check_performed=True,
            open_orders_count=0,
            order_test_performed=True,
            order_test_ok=False,
        )
    else:
        snapshot = risk_reducing_exit_preflight_snapshot(symbol=args.symbol)

    payload = {
        "contract_version": TRUTHFUL_ORDER_PREFLIGHT_VERSION,
        "ok": snapshot.ok,
        "scenario": args.scenario,
        "snapshot": snapshot.to_log_payload(),
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if snapshot.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
