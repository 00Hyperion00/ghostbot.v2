from __future__ import annotations

import argparse
import json
import py_compile
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tradebot.hyp006_shadow_runner_dry_run import (  # noqa: E402
    BRANCH_ID,
    BRANCH_NAME,
    CONTRACT_VERSION,
    STRATEGY_FAMILY,
    Candle,
    build_hyp006_shadow_runner_dry_run_report,
)

EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_runner_dry_run.py",
    "tools/run_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/check_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/apply_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/rollback_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tests/test_hyp006_shadow_runner_dry_run_4B436628C.py",
    "docs/HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_4B436628C.md",
]


def synthetic_registration_report() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.28B",
        "candidate_spec_draft": {
            "contract_version": "4B.4.3.6.6.28B",
            "hypothesis_id": "HYP-006",
            "branch_id": BRANCH_ID,
            "branch_name": BRANCH_NAME,
            "strategy_family": STRATEGY_FAMILY,
            "no_order_shadow_only": True,
            "approvals": {
                "approved_for_shadow_collection": False,
                "approved_for_training_candidate": False,
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "order_actions_allowed": False,
            },
            "registration_gate": {
                "registration_requires_28c_runner": True,
                "next_required_gate": "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL",
            },
            "entry_signal_definition": {
                "timeframe": "4h",
                "parameters": {
                    "lookback_bars": 3,
                    "hold_bars": 3,
                    "min_sweep_bps": 10.0,
                    "min_wick_pct_reference": 40.0,
                    "compression_window": 2,
                    "compression_baseline_bars": 4,
                    "max_compression_ratio_reference": 2.0,
                },
            },
            "required_shadow_acceptance_metrics": [
                {"name": "max_slippage_proxy_bps", "operator": "<=", "threshold": 12.0}
            ],
        },
    }


def synthetic_candles() -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[Candle] = []
    for idx in range(8):
        rows.append(
            Candle(
                timestamp_utc=(base + timedelta(hours=4 * idx)).isoformat(),
                symbol="BTCUSDT",
                open=101.0,
                high=102.0,
                low=100.0,
                close=101.0,
                volume=1000.0,
            )
        )
    rows.append(
        Candle(
            timestamp_utc=(base + timedelta(hours=32)).isoformat(),
            symbol="BTCUSDT",
            open=101.0,
            high=103.0,
            low=99.5,
            close=101.5,
            volume=2000.0,
        )
    )
    for step, close in enumerate((100.0, 99.0, 98.0), start=9):
        rows.append(
            Candle(
                timestamp_utc=(base + timedelta(hours=4 * step)).isoformat(),
                symbol="BTCUSDT",
                open=101.0,
                high=102.0,
                low=close - 0.5,
                close=close,
                volume=900.0,
            )
        )
    return rows


def py_compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def run_checks(project_root: Path) -> dict[str, Any]:
    expected = {item: (project_root / item).exists() for item in EXPECTED_FILES}
    compile_targets = [project_root / item for item in EXPECTED_FILES if item.endswith(".py")]
    compiled = {str(path.relative_to(project_root)): py_compile_ok(path) for path in compile_targets if path.exists()}
    report = build_hyp006_shadow_runner_dry_run_report(
        candidate_spec_source=synthetic_registration_report(),
        candles=synthetic_candles(),
        symbols=["BTCUSDT"],
        existing_ledger_rows=[],
        source_paths={"synthetic": True},
        network_request_performed=False,
        out_dir="reports/hyp006_r1_canonical",
    )
    bad_report = build_hyp006_shadow_runner_dry_run_report(
        candidate_spec_source={"contract_version": "BAD"},
        candles=synthetic_candles(),
        symbols=["BTCUSDT"],
        existing_ledger_rows=[],
        network_request_performed=False,
        out_dir="reports/hyp006_r1_canonical",
    )
    summary = report.get("dry_run_summary", {})
    preflight = report.get("scheduler_registration_preflight", {})
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": bool(compiled) and all(compiled.values()),
        "contract_version_ok": report.get("contract_version") == CONTRACT_VERSION,
        "decision_ready": report.get("decision") == "HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_READY",
        "dry_run_observation_detected": summary.get("dry_run_observation_count", 0) >= 1,
        "short_return_positive_on_down_move": (summary.get("mean_return_bps") or 0) > 0,
        "operator_gate_ready": report.get("operator_registration_approval_gate_ready") is True,
        "scheduler_preflight_ready": report.get("canonical_scheduler_registration_preflight_ready") is True,
        "scheduler_task_not_created": preflight.get("scheduler_task_created") is False,
        "scheduler_mutation_blocked": report.get("scheduler_mutation_performed") is False,
        "shadow_collection_blocked": report.get("approved_for_shadow_collection") is False,
        "paper_approval_blocked": report.get("approved_for_paper_candidate") is False,
        "live_approval_blocked": report.get("approved_for_live_real") is False,
        "training_blocked": report.get("training_performed") is False,
        "invalid_spec_fail_closed": bad_report.get("ok") is False and bad_report.get("approved_for_shadow_collection") is False,
        "network_not_required_for_checker": report.get("network_request_performed") is False,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    result = run_checks(PROJECT_ROOT)
    if args.once_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} checker ok={result['ok']}")
        for name, value in result["checks"].items():
            print(f" - {name}: {value}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
