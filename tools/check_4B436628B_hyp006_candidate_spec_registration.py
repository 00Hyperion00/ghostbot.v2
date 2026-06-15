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

CONTRACT_VERSION = "4B.4.3.6.6.28B"
EXPECTED = [
    ROOT / "src" / "tradebot" / "hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "run_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "check_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "apply_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "rollback_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tests" / "test_hyp006_candidate_spec_registration_4B436628B.py",
    ROOT / "docs" / "HYP006_R1_CANDIDATE_SPEC_REGISTRATION_4B436628B.md",
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _synthetic_discovery() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.28A",
        "decision": "HYP005_FAILED_BRANCH_LESSONS_CANDIDATE_DISCOVERY_READY",
        "selected_research_candidate": {
            "candidate_id": "HYP-006-R1",
            "branch_name": "failed_downside_sweep_reversal_continuation_short",
            "score": 63.361056,
            "risk_level": "HIGH",
            "expected_edge_proxy_bps": 115.12272,
            "approved_for_candidate_spec_drafting": True,
            "approved_for_shadow_collection": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
        },
    }


def build_status() -> dict[str, Any]:
    from tradebot.hyp006_candidate_spec_registration import build_hyp006_registration_gate_report

    files_present = all(path.exists() for path in EXPECTED)
    compile_ok = all(_compile(path) for path in EXPECTED if path.suffix == ".py" and path.exists())
    report = build_hyp006_registration_gate_report(discovery_report=_synthetic_discovery())
    spec = report.get("candidate_spec_draft") or {}
    gate = spec.get("registration_gate") or {}
    approvals = spec.get("approvals") or {}
    checks = {
        "all_expected_files_present": files_present,
        "all_py_compile_ok": compile_ok,
        "contract_version_ok": report.get("contract_version") == CONTRACT_VERSION,
        "decision_ready": report.get("decision") == "HYP006_R1_CANDIDATE_SPEC_DRAFT_REGISTRATION_GATE_READY",
        "candidate_spec_draft_ready": report.get("candidate_spec_draft_ready") is True,
        "hyp006_selected": report.get("selected_candidate_id") == "HYP-006-R1",
        "registration_candidate_ready": report.get("approved_for_no_order_shadow_registration_candidate") is True,
        "requires_28c": report.get("next_required_gate") == "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL" and gate.get("registration_requires_28c_runner") is True,
        "shadow_collection_blocked": report.get("approved_for_shadow_collection") is False and approvals.get("approved_for_shadow_collection") is False,
        "paper_approval_blocked": report.get("approved_for_paper_candidate") is False and approvals.get("approved_for_paper_candidate") is False,
        "live_approval_blocked": report.get("approved_for_live_real") is False and approvals.get("approved_for_live_real") is False,
        "training_blocked": report.get("training_performed") is False and approvals.get("approved_for_training_candidate") is False,
        "strategy_mutation_blocked": report.get("strategy_parameter_mutation_performed") is False,
        "scheduler_mutation_blocked": report.get("scheduler_mutation_performed") is False,
        "no_order_candidate_spec_only": report.get("no_order_candidate_spec_draft_only") is True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "branch_state_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
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
