from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/hyp006_scheduler_health_verify.py",
    "tools/run_4B436628E_hyp006_scheduler_execution_health.py",
    "tools/check_4B436628E_hyp006_scheduler_execution_health.py",
    "tools/apply_4B436628E_hyp006_scheduler_execution_health.py",
    "tools/rollback_4B436628E_hyp006_scheduler_execution_health.py",
    "tests/test_hyp006_scheduler_execution_health_4B436628E.py",
    "docs/HYP006_R1_SCHEDULER_EXECUTION_HEALTH_4B436628E.md",
    "README_APPLY_4B436628E.txt",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    removed = 0
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed += 1
    print(f"4B.4.3.6.6.28E rollback removed_files={removed}")
    print("scheduler_mutation_performed: False")
    print("scheduler_task_deleted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
