from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.position_sizing import (  # noqa: E402
    POSITION_SIZING_CONTRACT_VERSION,
    PositionSizingError,
    build_entry_sizing_decision,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only 27F position sizing contract checker")
    parser.add_argument("--sizing-mode", default="fixed_quote")
    parser.add_argument("--free-quote-balance", type=float, default=1000.0)
    parser.add_argument("--quote-balance-reserve-usd", type=float, default=0.0)
    parser.add_argument("--max-quote-budget-usd", type=float, default=0.0)
    parser.add_argument("--order-notional-usd", type=float, default=25.0)
    parser.add_argument("--risk-percent-quote-balance", type=float, default=2.5)
    parser.add_argument("--price", type=float, default=2500.0)
    parser.add_argument("--step-size", type=float, default=0.0001)
    parser.add_argument("--min-qty", type=float, default=0.0001)
    parser.add_argument("--max-qty", type=float, default=1000.0)
    parser.add_argument("--min-notional", type=float, default=5.0)
    parser.add_argument("--min-notional-buffer-multiplier", type=float, default=1.10)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    settings = SimpleNamespace(
        sizing_mode=args.sizing_mode,
        free_quote_balance=args.free_quote_balance,
        quote_balance_reserve_usd=args.quote_balance_reserve_usd,
        max_quote_budget_usd=args.max_quote_budget_usd,
        order_notional_usd=args.order_notional_usd,
        risk_percent_quote_balance=args.risk_percent_quote_balance,
        min_notional_buffer_multiplier=args.min_notional_buffer_multiplier,
    )
    rules = SimpleNamespace(
        step_size=args.step_size,
        min_qty=args.min_qty,
        max_qty=args.max_qty,
        min_notional=args.min_notional,
    )
    try:
        decision = build_entry_sizing_decision(
            settings=settings,
            symbol_rules=rules,
            free_quote_balance=args.free_quote_balance,
            reference_price=args.price,
        )
        payload = {
            "ok": True,
            "reason_code": decision.reason_code,
            "contract_version": POSITION_SIZING_CONTRACT_VERSION,
            "decision": decision.to_dict(),
            "read_only": True,
            "network_request_performed": False,
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
        }
        exit_code = 0
    except PositionSizingError as error:
        payload = {
            "ok": False,
            "reason_code": error.reason_code,
            "contract_version": POSITION_SIZING_CONTRACT_VERSION,
            "decision": None,
            "read_only": True,
            "network_request_performed": False,
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
        }
        exit_code = 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
