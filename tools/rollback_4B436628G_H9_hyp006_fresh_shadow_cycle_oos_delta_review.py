from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/tradebot/hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tests/test_hyp006_fresh_shadow_cycle_oos_delta_review_4B436628G_H9.py",
    "tools/apply_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tools/check_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tools/run_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tools/rollback_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "docs/HYP006_R1_FRESH_SHADOW_CYCLE_OOS_DELTA_REVIEW_4B436628G_H9.md",
    "README_APPLY_4B436628G_H9.txt",
]


def main() -> int:
    removed = []
    for rel in FILES:
        path = ROOT / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print("4B.4.3.6.6.28G-H9 rollback completed")
    for item in removed:
        print(f" - removed: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
