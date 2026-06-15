from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CONTRACT_VERSION = "4B.4.3.6.6.28A"
EXPECTED = [
    ROOT / "src" / "tradebot" / "hypothesis_candidate_discovery.py",
    ROOT / "tools" / "run_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "check_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "apply_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "rollback_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tests" / "test_hypothesis_candidate_discovery_4B436628A.py",
    ROOT / "docs" / "NEW_HYPOTHESIS_CANDIDATE_DISCOVERY_4B436628A.md",
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _synthetic_report() -> dict[str, Any]:
    from tradebot.hypothesis_candidate_discovery import build_hypothesis_candidate_discovery_report

    rows = [
        {"observation_id": "A", "symbol": "ADAUSDT", "timestamp_utc": "2026-01-01T00:00:00+00:00", "forward_return_bps_final": -100.0},
        {"observation_id": "B", "symbol": "BTCUSDT", "timestamp_utc": "2026-01-01T00:00:00+00:00", "forward_return_bps_final": -200.0},
        {"observation_id": "C", "symbol": "ETHUSDT", "timestamp_utc": "2026-01-02T00:00:00+00:00", "forward_return_bps_final": 50.0},
    ]
    h3 = {"stagnation": {"status": "STAGNATED"}, "candidate_diagnostics": {"top_bottleneck_filter": "min_sweep_bps"}}
    h4 = {"research_summary": {"paper_transition_candidate_found": False, "promising_research_only_variant_count": 0, "best_research_status": "REJECTED_NEGATIVE_EXPECTANCY"}}
    h5 = {"closure_status": "CLOSE_NO_PROMOTION_RECOMMENDED", "closure_criteria": {"h3_stagnation_confirmed": True, "h4_relaxation_rejected": True, "sample_target_incomplete": True}}
    return build_hypothesis_candidate_discovery_report(ledger_rows=rows, h3_diagnostics=h3, h4_sensitivity=h4, h5_closure=h5)


def build_status() -> dict[str, Any]:
    files_present = all(path.exists() for path in EXPECTED)
    compile_ok = all(_compile(path) for path in EXPECTED if path.suffix == ".py" and path.exists())
    report = _synthetic_report()
    selected = report.get("selected_research_candidate") or {}
    checks = {
        "all_expected_files_present": files_present,
        "all_py_compile_ok": compile_ok,
        "contract_version_ok": report.get("contract_version") == CONTRACT_VERSION,
        "decision_ready": report.get("decision") == "HYP005_FAILED_BRANCH_LESSONS_CANDIDATE_DISCOVERY_READY",
        "failed_branch_lessons_integrated": "FAILED_BRANCH_NEGATIVE_EXPECTANCY" in report.get("failed_branch_lessons", {}).get("lesson_codes", []),
        "selected_candidate_present": bool(selected.get("candidate_id")),
        "selected_candidate_requires_28b": str(selected.get("required_next_gate", "")).startswith("28B"),
        "shadow_collection_not_approved": report.get("approved_for_shadow_collection") is False,
        "paper_approval_blocked": report.get("approved_for_paper_candidate") is False,
        "live_approval_blocked": report.get("approved_for_live_real") is False,
        "branch_state_mutation_blocked": report.get("branch_state_mutation_performed") is False,
        "strategy_mutation_blocked": report.get("strategy_parameter_mutation_performed") is False,
        "training_blocked": report.get("training_performed") is False,
        "no_order_research_only": report.get("no_order_research_branch_selection_only") is True,
    }
    return {
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
        "branch_state_mutation_performed": False,
        "paper_live_order_enablement_present": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    status = build_status()
    if args.once_json:
        print(json.dumps(status, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"{CONTRACT_VERSION} checker ok={status['ok']}")
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
