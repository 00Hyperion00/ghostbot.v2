from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.training.candle_budget import TrainingCandleBudgetError, build_training_candle_budget


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only interval-aware training candle budget checker")
    parser.add_argument("--interval", required=True)
    parser.add_argument("--days", type=int, required=True)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    try:
        budget = build_training_candle_budget(args.interval, args.days)
        payload = {
            "ok": True,
            "read_only": True,
            **budget.to_dict(),
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "training_performed": False,
            "trading_action_performed": False,
        }
    except TrainingCandleBudgetError as error:
        payload = {
            "ok": False,
            "read_only": True,
            "interval": args.interval,
            "days": args.days,
            "reason_code": str(error),
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "training_performed": False,
            "trading_action_performed": False,
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
