from __future__ import annotations

import argparse
import json
import py_compile
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CONTRACT_VERSION = "4B.4.3.6.6.27G-H3"
MODULE = ROOT / "src" / "tradebot" / "hyp005_shadow_stagnation_diagnostics.py"
RUNNER = ROOT / "tools" / "run_4B436627GH3_shadow_stagnation_diagnostics.py"
TEST = ROOT / "tests" / "test_shadow_stagnation_diagnostics_4B436627GH3.py"
DOC = ROOT / "docs" / "SHADOW_OBSERVATION_STAGNATION_DIAGNOSTICS_4B436627GH3.md"


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _candle(offset: int, open_: float, high: float, low: float, close: float, symbol: str = "TESTUSDT") -> Any:
    from tradebot.hyp005_shadow_stagnation_diagnostics import Candle

    ts = datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(hours=4 * offset)
    return Candle(ts.isoformat(), symbol, open_, high, low, close, 1000.0)


def _fixture_report() -> dict[str, Any]:
    from tradebot.hyp005_shadow_stagnation_diagnostics import build_stagnation_diagnostics_report, stable_observation_id

    spec = {
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "entry_signal_definition": {
            "timeframe": "4h",
            "parameters": {
                "lookback_bars": 3,
                "hold_bars": 2,
                "min_sweep_bps": 20.0,
                "min_wick_pct": 40.0,
                "compression_window": 2,
                "compression_baseline_bars": 3,
                "max_compression_ratio": 2.0,
            },
        },
    }
    candles = [
        _candle(0, 100, 101, 99, 100),
        _candle(1, 100, 101, 99, 100),
        _candle(2, 100, 101, 99, 100),
        _candle(3, 100, 101, 99, 100),
        _candle(4, 98.5, 102, 98, 100.5),
        _candle(5, 100.5, 101, 99.5, 100.2),
        _candle(6, 100.2, 101, 99.9, 100.3),
        _candle(7, 100, 102, 97, 100.5),
        _candle(8, 100.5, 101, 100, 100.8),
        _candle(9, 100.8, 101.2, 100.1, 100.9),
    ]
    duplicate_id = stable_observation_id("TESTUSDT", "4h", candles[7].timestamp_utc)
    ledger = [{"observation_id": duplicate_id, "symbol": "TESTUSDT", "timeframe": "4h", "timestamp_utc": candles[4].timestamp_utc}]
    return build_stagnation_diagnostics_report(
        candidate_spec=spec,
        ledger_rows=ledger,
        candles=candles,
        generated_at="2026-06-15T00:00:00+00:00",
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only checker for 4B.4.3.6.6.27G-H3 stagnation diagnostics")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="gh3_checker_"):
        report = _fixture_report()

    runner_text = _read_text(RUNNER)
    module_text = _read_text(MODULE)
    result = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "checks": {
            "module_exists": MODULE.exists(),
            "runner_exists": RUNNER.exists(),
            "test_exists": TEST.exists(),
            "doc_exists": DOC.exists(),
            "module_py_compile_ok": _compile_ok(MODULE),
            "runner_py_compile_ok": _compile_ok(RUNNER),
            "test_py_compile_ok": _compile_ok(TEST),
            "contract_version_ok": report.get("contract_version") == CONTRACT_VERSION,
            "duplicate_candidate_detected": report.get("candidate_diagnostics", {}).get("duplicate_candidate_count", 0) >= 1,
            "near_miss_detected": report.get("candidate_diagnostics", {}).get("near_miss_count", 0) >= 1,
            "no_order_research_only": report.get("no_order_research_diagnostics_only") is True,
            "paper_approval_blocked": report.get("approved_for_paper_candidate") is False,
            "live_approval_blocked": report.get("approved_for_live_real") is False,
            "public_get_explicit_no_post": "method=\"GET\"" in module_text and "urlopen" in module_text,
            "runner_requires_review_ok": "--review-ok" in runner_text,
        },
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": any(
            marker in (module_text + runner_text)
            for marker in (
                "orders_allowed=True",
                "paper_trading_allowed=True",
                "live_trading_allowed=True",
                "approved_for_live_real: True",
                "approved_for_paper_candidate: True",
            )
        ),
    }
    result["ok"] = all(result["checks"].values()) and not result["paper_live_order_enablement_present"]
    if args.once_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} checker ok={result['ok']}")
        for key, value in result["checks"].items():
            print(f" - {key}: {value}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
