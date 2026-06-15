from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATED_FILES = [
    "src/tradebot/hyp006_shadow_sample_expansion_tracking.py",
    "tools/run_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/check_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/apply_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/rollback_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tests/test_hyp006_shadow_sample_expansion_tracking_4B436628G.py",
    "docs/HYP006_R1_SHADOW_SAMPLE_EXPANSION_TRACKING_4B436628G.md",
    "README_APPLY_4B436628G.txt",
]


def main() -> int:
    removed = 0
    for rel in CREATED_FILES:
        path = ROOT / rel
        if path.exists():
            path.unlink()
            removed += 1
    print(f"4B.4.3.6.6.28G rollback complete removed={removed}")
    print("scheduler_mutation_performed: False")
    print("trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
