from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "src/tradebot/hyp006_operator_cockpit_baseline.py",
    "tools/run_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tools/check_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tools/apply_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tests/test_hyp006_operator_cockpit_baseline_4B436628F.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_BASELINE_4B436628F.md",
    "README_APPLY_4B436628F.txt",
]


def main() -> int:
    removed: list[str] = []
    for rel in TARGETS:
        path = ROOT / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print("4B.4.3.6.6.28F rollback completed")
    for rel in removed:
        print(f" - removed: {rel}")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
