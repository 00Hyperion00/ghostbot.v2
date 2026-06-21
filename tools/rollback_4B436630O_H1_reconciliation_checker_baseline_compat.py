from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630O_H1.txt",
    "docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_CHECKER_BASELINE_COMPAT_4B436630O_H1.md",
    "tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py",
    "tools/apply_4B436630O_H1_reconciliation_checker_baseline_compat.py",
    "tools/rollback_4B436630O_H1_reconciliation_checker_baseline_compat.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H1.py",
]


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30O-H1 rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
