from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630Q.txt",
    "docs/FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_4B436630Q.md",
    "src/tradebot/first_paper_sandbox_canary_submit_gate.py",
    "tests/test_first_paper_sandbox_canary_submit_gate_4B436630Q.py",
    "tools/apply_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/check_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/rollback_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/run_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
]


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30Q rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
