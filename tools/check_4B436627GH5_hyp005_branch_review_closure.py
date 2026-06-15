from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp005_branch_review_closure import (  # noqa: E402
    CONTRACT_VERSION,
    build_branch_review_closure_report,
)

EXPECTED = [
    "README_APPLY_4B436627GH5.txt",
    "docs/HYP005_R1_BRANCH_REVIEW_CLOSURE_4B436627GH5.md",
    "src/tradebot/hyp005_branch_review_closure.py",
    "tests/test_hyp005_branch_review_closure_4B436627GH5.py",
    "tools/apply_4B436627GH5_hyp005_branch_review_closure.py",
    "tools/check_4B436627GH5_hyp005_branch_review_closure.py",
    "tools/rollback_4B436627GH5_hyp005_branch_review_closure.py",
    "tools/run_4B436627GH5_hyp005_branch_review_closure.py",
]
PY_FILES = [item for item in EXPECTED if item.endswith(".py")]


def _compile(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def _synthetic_ledger() -> list[dict[str, Any]]:
    return [
        {"observation_id": "HYP-005-BTCUSDT-4h-2026-06-01T000000Z", "symbol": "BTCUSDT", "timeframe": "4h", "timestamp_utc": "2026-06-01T00:00:00+00:00", "forward_return_bps_final": -120.0},
        {"observation_id": "HYP-005-ETHUSDT-4h-2026-06-01T040000Z", "symbol": "ETHUSDT", "timeframe": "4h", "timestamp_utc": "2026-06-01T04:00:00+00:00", "forward_return_bps_final": 20.0},
        {"observation_id": "HYP-005-XRPUSDT-4h-2026-06-01T080000Z", "symbol": "XRPUSDT", "timeframe": "4h", "timestamp_utc": "2026-06-01T08:00:00+00:00", "forward_return_bps_final": -80.0},
    ]


def _synthetic_h3() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.27G-H3",
        "decision": "HYP005_SHADOW_STAGNATION_DIAGNOSTICS_READY",
        "stagnation": {"status": "STAGNATED", "new_unique_observation_available": False, "duplicate_only_current_candidates": True, "days_since_latest_observation": 10.0},
        "candidate_diagnostics": {"exact_candidate_count": 21, "new_unique_candidate_count": 0, "duplicate_candidate_count": 21, "near_miss_count": 73, "top_bottleneck_filter": "min_sweep_bps"},
    }


def _synthetic_h4() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.27G-H4",
        "decision": "HYP005_PARAMETER_SENSITIVITY_MATRIX_READY",
        "research_summary": {
            "variant_count": 27,
            "variants_with_new_unique_candidates": 26,
            "promising_research_only_variant_count": 0,
            "paper_transition_candidate_found": False,
            "strategy_parameter_mutation_recommended": False,
            "best_research_variant_id": "sweep_12p0__wick_38p0__compression_1p15",
            "best_research_status": "REJECTED_NEGATIVE_EXPECTANCY",
        },
        "top_variants": [{"variant_id": "sweep_12p0__wick_38p0__compression_1p15", "new_unique_candidate_count": 10, "performance": {"net_return_bps": -4100.0, "mean_return_bps": -132.0, "profit_factor": 0.29}}],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    compile_results = {path: _compile(ROOT / path) for path in PY_FILES if (ROOT / path).exists()}
    report = build_branch_review_closure_report(
        ledger_rows=_synthetic_ledger(),
        h3_report=_synthetic_h3(),
        h4_report=_synthetic_h4(),
        operator_snapshot={"mode": "SHADOW", "audit": {"paper_transition_ready": False, "approved_for_paper_candidate": False, "approved_for_live_real": False}},
    )
    checks = {
        "contract_version_ok": CONTRACT_VERSION == "4B.4.3.6.6.27G-H5",
        "all_expected_files_present": all((ROOT / item).exists() for item in EXPECTED),
        "all_py_compile_ok": len(compile_results) == len(PY_FILES) and all(compile_results.values()),
        "closure_recommended": bool(report.get("branch_closure_recommended")),
        "decision_ready": report.get("decision") == "HYP005_R1_BRANCH_REVIEW_NO_PROMOTION_CLOSURE_READY",
        "paper_approval_blocked": report.get("approved_for_paper_candidate") is False,
        "live_approval_blocked": report.get("approved_for_live_real") is False,
        "training_blocked": report.get("approved_for_training_candidate") is False,
        "branch_state_mutation_blocked": report.get("branch_state_mutation_performed") is False,
        "strategy_mutation_blocked": report.get("strategy_parameter_mutation_performed") is False,
        "operator_review_required": report.get("operator_review_required_for_closure") is True,
        "no_order_branch_review_only": report.get("no_order_branch_review_only") is True,
    }
    payload = {
        "ok": all(checks.values()),
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
    if args.once_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} checker ok={payload['ok']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
