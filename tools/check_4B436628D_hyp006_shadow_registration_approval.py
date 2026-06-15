from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CONTRACT_VERSION = "4B.4.3.6.6.28D"
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_registration_operator_approval.py",
    "src/tradebot/hyp006_shadow_runner_dry_run.py",
    "tools/run_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/run_4B436628D_hyp006_canonical_shadow_cycle.py",
    "tools/check_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/apply_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/rollback_4B436628D_hyp006_shadow_registration_approval.py",
    "tests/test_hyp006_shadow_registration_approval_4B436628D.py",
    "docs/HYP006_R1_CANONICAL_SHADOW_REGISTRATION_4B436628D.md",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def synthetic_28c_report() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28C",
        "decision": "HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_READY",
        "hypothesis_id": "HYP-006",
        "branch_id": "HYP-006-R1",
        "branch_name": "failed_downside_sweep_reversal_continuation_short",
        "runner_dry_run_ready": True,
        "operator_registration_approval_gate_ready": True,
        "canonical_scheduler_registration_preflight_ready": True,
        "approved_for_no_order_shadow_collection_registration_candidate": True,
        "approved_for_shadow_collection": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "approved_for_training_candidate": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
        "dry_run_summary": {"new_unique_dry_run_observation_count": 3, "profit_factor": 2.0},
        "symbols_requested": ["TESTUSDT"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    from tradebot.hyp006_shadow_registration_operator_approval import (  # noqa: E402
        build_registration_approval_report,
        build_runtime_artifact_retention_policy,
        validate_28c_dry_run_report,
    )

    expected = {item: (ROOT / item).exists() for item in EXPECTED_FILES}
    compiled = {item: compile_ok(ROOT / item) for item in PY_FILES if (ROOT / item).exists()}
    dry_run_ok, _ = validate_28c_dry_run_report(synthetic_28c_report())
    approved = build_registration_approval_report(
        dry_run_report=synthetic_28c_report(),
        operator_approval=True,
        reports_dir="reports/hyp006_r1_canonical",
        symbols=["TESTUSDT"],
    )
    blocked = build_registration_approval_report(
        dry_run_report=synthetic_28c_report(),
        operator_approval=False,
        reports_dir="reports/hyp006_r1_canonical",
        symbols=["TESTUSDT"],
    )
    retention = build_runtime_artifact_retention_policy()
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": bool(compiled) and all(compiled.values()),
        "contract_version_ok": approved.get("contract_version") == CONTRACT_VERSION,
        "valid_28c_dry_run_accepted": dry_run_ok,
        "operator_approval_required": blocked.get("ok") is False,
        "registration_approval_ready": approved.get("ok") is True,
        "approved_for_shadow_collection_only_after_operator_approval": approved.get("approved_for_shadow_collection") is True,
        "paper_approval_blocked": approved.get("approved_for_paper_candidate") is False,
        "live_approval_blocked": approved.get("approved_for_live_real") is False,
        "training_blocked": approved.get("approved_for_training_candidate") is False,
        "scheduler_mutation_blocked": approved.get("scheduler_mutation_performed") is False,
        "scheduler_task_not_created": approved.get("scheduler_task_created") is False,
        "retention_policy_present": retention.get("policy_name") == "hyp006_r1_runtime_artifact_retention_policy",
        "gitignore_not_mutated": retention.get("gitignore_mutation_performed") is False,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(payload)
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
