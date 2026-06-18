from __future__ import annotations

from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28G-H4"
ADDED_FILES = [
    "src/tradebot/hyp006_near_miss_outcome_attribution.py",
    "tools/run_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tools/apply_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tools/check_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tools/rollback_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tests/test_hyp006_near_miss_outcome_attribution_4B436628G_H4.py",
    "docs/HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_4B436628G_H4.md",
]


def main() -> int:
    root = Path.cwd()
    removed = []
    for relative in ADDED_FILES:
        target = root / relative
        if target.exists():
            target.unlink()
            removed.append(relative)
    print(f"{CONTRACT_VERSION} rollback removed {len(removed)} files")
    for item in removed:
        print(f" - removed: {item}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
