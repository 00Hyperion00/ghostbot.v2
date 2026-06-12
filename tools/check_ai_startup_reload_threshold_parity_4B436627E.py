from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.ai.decision_contract import (  # noqa: E402
    AI_DECISION_CONTRACT_VERSION,
    AIDecisionContractError,
    assert_startup_reload_parity,
    build_decision_contract,
    decision_contract_diff,
)


@dataclass(slots=True)
class _ReloadPayload:
    threshold: float | None = None
    buy_threshold: float | None = None
    sell_threshold: float | None = None
    hold_band_low: float | None = None
    hold_band_high: float | None = None
    indecision_margin: float | None = None
    threshold_profile: str | None = None


def _contract_from_args(args: argparse.Namespace, *, prefix: str, fallback: Any = None):
    return build_decision_contract(
        threshold=getattr(args, f"{prefix}_threshold"),
        buy_threshold=getattr(args, f"{prefix}_buy_threshold"),
        sell_threshold=getattr(args, f"{prefix}_sell_threshold"),
        hold_band_low=getattr(args, f"{prefix}_hold_band_low"),
        hold_band_high=getattr(args, f"{prefix}_hold_band_high"),
        indecision_margin=getattr(args, f"{prefix}_indecision_margin"),
        threshold_profile=getattr(args, f"{prefix}_threshold_profile"),
        fallback=fallback,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only AI startup/reload decision contract parity checker")
    for prefix in ("startup", "reload"):
        parser.add_argument(f"--{prefix}-threshold", type=float, default=None)
        parser.add_argument(f"--{prefix}-buy-threshold", type=float, default=None)
        parser.add_argument(f"--{prefix}-sell-threshold", type=float, default=None)
        parser.add_argument(f"--{prefix}-hold-band-low", type=float, default=None)
        parser.add_argument(f"--{prefix}-hold-band-high", type=float, default=None)
        parser.add_argument(f"--{prefix}-indecision-margin", type=float, default=None)
        parser.add_argument(f"--{prefix}-threshold-profile", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    try:
        startup = _contract_from_args(args, prefix="startup")
        reload_contract = _contract_from_args(args, prefix="reload", fallback=startup)
        assert_startup_reload_parity(startup, reload_contract)
        report = {
            "ok": True,
            "reason_code": "MODEL_DECISION_CONTRACT_PARITY_VERIFIED",
            "contract_version": AI_DECISION_CONTRACT_VERSION,
            "startup_contract": startup.snapshot(),
            "reload_contract": reload_contract.snapshot(),
            "diff": {},
            "read_only": True,
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except AIDecisionContractError as error:
        startup = locals().get("startup")
        reload_contract = locals().get("reload_contract")
        report = {
            "ok": False,
            "reason_code": str(error),
            "contract_version": AI_DECISION_CONTRACT_VERSION,
            "startup_contract": startup.snapshot() if startup is not None else None,
            "reload_contract": reload_contract.snapshot() if reload_contract is not None else None,
            "diff": decision_contract_diff(startup, reload_contract) if startup is not None and reload_contract is not None else {},
            "read_only": True,
            "config_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
