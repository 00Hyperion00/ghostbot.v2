from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/tradebot/paper_transition_operator_gate.py",
    "tests/test_paper_transition_operator_gate_4B436630B.py",
    "tools/check_4B436630B_paper_transition_operator_approval_gate.py",
    "tools/run_4B436630B_paper_transition_operator_approval_gate.py",
    "docs/PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_4B436630B.md",
]


def main() -> int:
    for rel in FILES:
        path = ROOT / rel
        if path.exists():
            path.unlink()
            print(f"removed {rel}")
    print("rollback complete; config.py 30B fields are intentionally left for manual review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
