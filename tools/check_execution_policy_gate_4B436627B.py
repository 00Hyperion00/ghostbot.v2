from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.binance_environment import resolve_binance_environment  # noqa: E402
from tradebot.config import Settings  # noqa: E402
from tradebot.execution_policy import (  # noqa: E402
    EXECUTION_POLICY_GATE_VERSION,
    ExecutionPolicyError,
    build_execution_policy_snapshot,
    enforce_execution_policy,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only exchange-level execution policy checker")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--market-type", default="spot_demo")
    parser.add_argument("--base-url", default="https://demo-api.binance.com")
    parser.add_argument("--execution-mode", default="live_demo")
    parser.add_argument("--live-trading-armed", action="store_true")
    parser.add_argument("--live-real-double-confirm", action="store_true")
    parser.add_argument("--action", default="ENTRY_NEW_RISK")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    if args.config:
        settings = Settings.from_yaml(args.config)
    else:
        settings = Settings(
            market_type=args.market_type,
            base_url=args.base_url,
            execution_mode=args.execution_mode,
            live_trading_armed=bool(args.live_trading_armed),
            live_real_double_confirm=bool(args.live_real_double_confirm),
        )
    try:
        profile = resolve_binance_environment(settings.market_type, settings.base_url)
        snapshot = build_execution_policy_snapshot(settings, profile)
        try:
            decision = enforce_execution_policy(settings, profile, action=args.action)
            result = {
                "policy_version": EXECUTION_POLICY_GATE_VERSION,
                "ok": True,
                "fail_closed": True,
                "decision": decision.to_snapshot(),
                "snapshot": snapshot,
                "read_only": True,
                "config_mutation_performed": False,
                "scheduler_mutation_performed": False,
                "trading_action_performed": False,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ExecutionPolicyError as error:
            result = {
                "policy_version": EXECUTION_POLICY_GATE_VERSION,
                "ok": False,
                "fail_closed": True,
                "decision": error.to_snapshot(),
                "snapshot": snapshot,
                "read_only": True,
                "config_mutation_performed": False,
                "scheduler_mutation_performed": False,
                "trading_action_performed": False,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1
    except Exception as error:
        result = {
            "policy_version": EXECUTION_POLICY_GATE_VERSION,
            "ok": False,
            "fail_closed": True,
            "reason_code": getattr(error, "code", error.__class__.__name__),
            "message": str(error),
            "read_only": True,
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "trading_action_performed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
