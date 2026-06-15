from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CONTRACT_VERSION = "4B.4.3.6.6.27G-H4"
MODULE = ROOT / "src" / "tradebot" / "hyp005_shadow_parameter_sensitivity.py"
H3_MODULE = ROOT / "src" / "tradebot" / "hyp005_shadow_stagnation_diagnostics.py"
RUNNER = ROOT / "tools" / "run_4B436627GH4_shadow_parameter_sensitivity_matrix.py"
TEST = ROOT / "tests" / "test_shadow_parameter_sensitivity_matrix_4B436627GH4.py"
DOC = ROOT / "docs" / "SHADOW_PARAMETER_SENSITIVITY_MATRIX_4B436627GH4.md"


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _synthetic_report_ok() -> dict[str, bool]:
    from tradebot.hyp005_shadow_parameter_sensitivity import build_parameter_sensitivity_report
    from tradebot.hyp005_shadow_stagnation_diagnostics import Candle

    candles: list[Candle] = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for idx in range(80):
        candles.append(
            Candle(
                timestamp_utc=(start + timedelta(hours=4 * idx)).isoformat(),
                symbol="TESTUSDT",
                open=100.4,
                high=101.0,
                low=100.0,
                close=100.5,
                volume=1000.0,
            )
        )
    candles[60] = Candle(
        timestamp_utc="2026-01-11T00:00:00+00:00",
        symbol="TESTUSDT",
        open=100.3,
        high=100.4,
        low=99.85,
        close=100.2,
        volume=2000.0,
    )
    for idx in range(61, 68):
        candles[idx] = Candle(
            timestamp_utc=(start + timedelta(hours=4 * idx)).isoformat(),
            symbol="TESTUSDT",
            open=100.2,
            high=101.2,
            low=100.0,
            close=101.0,
            volume=1000.0,
        )
    report = build_parameter_sensitivity_report(
        candidate_spec=None,
        ledger_rows=[],
        candles=candles,
        min_sweep_bps_values=[18.0, 12.0],
        min_wick_pct_values=[42.0],
        max_compression_ratio_values=[1.05],
        generated_at="2026-01-12T00:00:00+00:00",
    )
    matrix = report.get("sensitivity_matrix", [])
    relaxed = [row for row in matrix if row.get("thresholds", {}).get("min_sweep_bps") == 12.0]
    return {
        "synthetic_ok": bool(report.get("ok")),
        "synthetic_paper_blocked": report.get("approved_for_paper_candidate") is False,
        "synthetic_live_blocked": report.get("approved_for_live_real") is False,
        "synthetic_relaxed_variant_detects_new_unique": bool(relaxed and relaxed[0].get("new_unique_candidate_count", 0) >= 1),
    }


def run_checks() -> dict[str, Any]:
    runner_text = RUNNER.read_text(encoding="utf-8") if RUNNER.exists() else ""
    module_text = MODULE.read_text(encoding="utf-8") if MODULE.exists() else ""
    checks: dict[str, bool] = {
        "h3_dependency_exists": H3_MODULE.exists(),
        "module_exists": MODULE.exists(),
        "module_py_compile_ok": MODULE.exists() and _compile_ok(MODULE),
        "runner_exists": RUNNER.exists(),
        "runner_py_compile_ok": RUNNER.exists() and _compile_ok(RUNNER),
        "test_exists": TEST.exists(),
        "test_py_compile_ok": TEST.exists() and _compile_ok(TEST),
        "doc_exists": DOC.exists(),
        "contract_version_ok": CONTRACT_VERSION in module_text,
        "threshold_grid_present": "threshold_grid" in module_text,
        "sensitivity_matrix_present": "sensitivity_matrix" in module_text,
        "runner_requires_review_ok": "--review-ok" in runner_text,
        "public_get_explicit": "method=\"GET\"" in runner_text,
        "paper_approval_blocked": '"approved_for_paper_candidate": False' in module_text,
        "live_approval_blocked": '"approved_for_live_real": False' in module_text,
        "strategy_mutation_blocked": '"strategy_parameter_mutation_performed": False' in module_text,
    }
    checks.update(_synthetic_report_ok() if checks["module_py_compile_ok"] and checks["h3_dependency_exists"] else {})
    ok = all(checks.values())
    return {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
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
    parser = argparse.ArgumentParser(description="27G-H4 read-only checker")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = run_checks()
    if args.once_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} checker ok={payload['ok']}")
        for key, value in payload["checks"].items():
            print(f" - {key}: {value}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
