from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630O_H2.txt",
    "docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_CHECKER_PROBE_SIGNATURE_4B436630O_H2.md",
    "tools/apply_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py",
    "tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py",
    "tools/rollback_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H2.py",
]


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30O-H2 rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
