from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630R.txt",
    "docs/PAPER_SANDBOX_CANARY_RECONCILIATION_4B436630R.md",
    "src/tradebot/paper_sandbox_canary_reconciliation.py",
    "tests/test_paper_sandbox_canary_reconciliation_4B436630R.py",
    "tools/apply_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/check_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/rollback_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/run_4B436630R_paper_sandbox_canary_reconciliation.py",
]


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30R rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
