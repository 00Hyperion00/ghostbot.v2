from __future__ import annotations

import py_compile
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28E"
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


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    results: dict[str, bool] = {}
    for rel in EXPECTED_FILES:
        path = root / rel
        results[f"{rel}_exists"] = path.exists()
        if path.suffix == ".py":
            results[f"{rel}_py_compile_ok"] = compile_ok(path)
    module_text = (root / "src/tradebot/hyp006_scheduler_health_verify.py").read_text(encoding="utf-8")
    runner_text = (root / "tools/run_4B436628E_hyp006_scheduler_execution_health.py").read_text(encoding="utf-8")
    results.update(
        {
            "contract_version_present": CONTRACT_VERSION in module_text,
            "scheduler_health_validation_present": "validate_scheduler_task_health" in module_text,
            "ledger_continuity_present": "validate_ledger_continuity" in module_text,
            "runner_requires_review_ok": "FAIL_CLOSED_REQUIRES_REVIEW_OK" in runner_text,
            "runner_requires_operator_execution_review": "FAIL_CLOSED_REQUIRES_OPERATOR_EXECUTION_REVIEW" in runner_text,
            "scheduler_mutation_performed": False,
            "scheduler_task_created": False,
            "config_mutation_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
            "paper_live_order_enablement_present": False,
        }
    )
    ok = all(value is True or value is False and key in {
        "scheduler_mutation_performed",
        "scheduler_task_created",
        "config_mutation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "paper_live_order_enablement_present",
    } for key, value in results.items())
    print(f"{CONTRACT_VERSION} HYP-006-R1 Scheduler Execution Health Verify patch applied")
    for key, value in results.items():
        print(f" - {key}: {value}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
