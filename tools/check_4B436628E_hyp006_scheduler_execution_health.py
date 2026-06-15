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

from tradebot.hyp006_scheduler_health_verify import (  # noqa: E402
    BRANCH_ID,
    CONTRACT_VERSION,
    PROPOSED_SCHEDULER_TASK_NAME,
    build_scheduler_execution_health_report,
)

EXPECTED_FILES = [
    "src/tradebot/hyp006_scheduler_health_verify.py",
    "tools/run_4B436628E_hyp006_scheduler_execution_health.py",
    "tools/check_4B436628E_hyp006_scheduler_execution_health.py",
    "tools/rollback_4B436628E_hyp006_scheduler_execution_health.py",
    "tests/test_hyp006_scheduler_execution_health_4B436628E.py",
    "docs/HYP006_R1_SCHEDULER_EXECUTION_HEALTH_4B436628E.md",
]


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def synthetic_inputs() -> tuple[dict, dict, list[dict], dict]:
    registration = {
        "contract_version": "4B.4.3.6.6.28D",
        "decision": "HYP006_R1_CANONICAL_NO_ORDER_SHADOW_REGISTRATION_APPROVED",
        "approved_for_canonical_no_order_shadow_registration": True,
        "approved_for_shadow_collection": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
    }
    cycle = {
        "contract_version": "4B.4.3.6.6.28D",
        "decision": "HYP006_R1_CANONICAL_NO_ORDER_SHADOW_COLLECTION_CYCLE_READY",
        "branch_id": BRANCH_ID,
        "approved_for_shadow_collection": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
        "shadow_summary": {
            "shadow_observation_count": 2,
            "new_unique_shadow_observation_count": 2,
        },
    }
    rows = [
        {"contract_version": "4B.4.3.6.6.28D", "branch_id": BRANCH_ID, "observation_id": "HYP-006-AAA", "symbol": "BTCUSDT", "forward_return_bps_final_short_probe": 25.0},
        {"contract_version": "4B.4.3.6.6.28D", "branch_id": BRANCH_ID, "observation_id": "HYP-006-BBB", "symbol": "ETHUSDT", "forward_return_bps_final_short_probe": -10.0},
    ]
    task_probe = {
        "exists": True,
        "task_name": PROPOSED_SCHEDULER_TASK_NAME,
        "state": "Ready",
        "last_task_result": 0,
        "number_of_missed_runs": 0,
        "action_execute": "python",
        "action_arguments": "tools/run_4B436628D_hyp006_canonical_shadow_cycle.py --registration-approval-json reports/x.json --registration-json reports/y.json --out-dir reports/hyp006_r1_canonical --review-ok",
        "working_directory": "C:/Users/muhas/OneDrive/Masaüstü/trade_botV2",
    }
    return registration, cycle, rows, task_probe


def build_checks(root: Path) -> dict[str, object]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = {rel: compile_ok(root / rel) for rel in EXPECTED_FILES if rel.endswith(".py")}
    registration, cycle, rows, task_probe = synthetic_inputs()
    payload = build_scheduler_execution_health_report(
        registration_approval_report=registration,
        cycle_report=cycle,
        ledger_rows=rows,
        task_probe=task_probe,
        operator_execution_review=True,
    )
    invalid_payload = build_scheduler_execution_health_report(
        registration_approval_report=registration,
        cycle_report=cycle,
        ledger_rows=rows,
        task_probe={"exists": False, "task_name": PROPOSED_SCHEDULER_TASK_NAME},
        operator_execution_review=True,
    )
    return {
        "contract_version_ok": payload.get("contract_version") == CONTRACT_VERSION,
        "decision_ready": payload.get("decision") == "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY",
        "synthetic_ok": payload.get("ok") is True,
        "invalid_scheduler_fail_closed": invalid_payload.get("ok") is False,
        "scheduler_health_ready": payload.get("scheduler_task_health_validation", {}).get("ok") is True,
        "ledger_continuity_ready": payload.get("ledger_continuity_validation", {}).get("ok") is True,
        "paper_approval_blocked": payload.get("approved_for_paper_candidate") is False,
        "live_approval_blocked": payload.get("approved_for_live_real") is False,
        "training_blocked": payload.get("training_performed") is False,
        "scheduler_mutation_blocked": payload.get("scheduler_mutation_performed") is False,
        "scheduler_task_not_created": payload.get("scheduler_task_created") is False,
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
    }, expected, compiled


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    checks, expected, compiled = build_checks(ROOT)
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
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    print(text)
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
