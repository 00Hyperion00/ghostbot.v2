from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.position_sizing import (  # noqa: E402
    STABLE_ENTRY_SKIP_CODE_COMPAT_VERSION,
    stable_entry_skip_code_for_sizing_error,
)

ENGINE = PROJECT_ROOT / "src" / "tradebot" / "engine.py"
RISK_GUARDS_TEST = PROJECT_ROOT / "tests" / "test_risk_guards.py"
ENTRY_LIFECYCLE_TEST = PROJECT_ROOT / "tests" / "test_entry_lifecycle_guard.py"
LIVE_DEMO_LIFECYCLE_TEST = PROJECT_ROOT / "tests" / "test_live_demo_order_lifecycle_hardening.py"


def _contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8")


def build_snapshot() -> dict[str, object]:
    checks = {
        "compat_version_ok": STABLE_ENTRY_SKIP_CODE_COMPAT_VERSION == "4B.4.3.6.6.27F-H1",
        "min_notional_mapping_ok": stable_entry_skip_code_for_sizing_error("SIZING_QUOTE_BUDGET_BELOW_MIN_NOTIONAL") == "MIN_NOTIONAL_BLOCKED",
        "insufficient_balance_mapping_ok": stable_entry_skip_code_for_sizing_error("SIZING_USABLE_QUOTE_BALANCE_NON_POSITIVE") == "INSUFFICIENT_QUOTE_BALANCE",
        "unknown_sizing_mapping_fail_closed_ok": stable_entry_skip_code_for_sizing_error("SIZING_REFERENCE_PRICE_NON_POSITIVE") == "ENTRY_SIZING_BLOCKED",
        "raw_sizing_reason_preserved": _contains(ENGINE, "'sizingReasonCode': error.reason_code"),
        "mandatory_preflight_adapter_gate_present": _contains(ENGINE, "PREFLIGHT_ADAPTER_UNAVAILABLE"),
        "unexpected_preflight_failure_gate_present": _contains(ENGINE, "PREFLIGHT_ADAPTER_CALL_FAILED"),
        "truthful_preflight_call_preserved": _contains(ENGINE, "await self.exchange.run_entry_order_preflight("),
        "risk_guards_test_double_updated": _contains(RISK_GUARDS_TEST, "async def run_entry_order_preflight("),
        "entry_lifecycle_test_double_updated": _contains(ENTRY_LIFECYCLE_TEST, "async def run_entry_order_preflight("),
        "live_demo_lifecycle_test_double_updated": _contains(LIVE_DEMO_LIFECYCLE_TEST, "async def run_entry_order_preflight("),
    }
    return {
        "ok": all(checks.values()),
        "contract_version": "4B.4.3.6.6.27F-H1",
        "checks": checks,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    snapshot = build_snapshot()
    if args.once_json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print("4B.4.3.6.6.27F-H1 read-only hotfix verification")
        for key, value in snapshot.items():
            print(f" - {key}: {value}")
    return 0 if bool(snapshot["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
