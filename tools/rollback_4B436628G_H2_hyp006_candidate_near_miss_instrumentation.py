from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/hyp006_candidate_near_miss_instrumentation.py",
    "tools/run_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tools/apply_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tools/check_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tools/rollback_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tests/test_hyp006_candidate_near_miss_instrumentation_4B436628G_H2.py",
    "docs/HYP006_R1_CANDIDATE_NEAR_MISS_INSTRUMENTATION_4B436628G_H2.md",
    "README_APPLY_4B436628G_H2.txt",
]


def main() -> int:
    root = Path.cwd()
    removed: list[str] = []
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print("4B.4.3.6.6.28G-H2 rollback completed")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    for rel in removed:
        print(f" - removed: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
