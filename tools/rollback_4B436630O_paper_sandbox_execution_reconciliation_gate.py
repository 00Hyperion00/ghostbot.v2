from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630O.txt",
    "docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_4B436630O.md",
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py",
    "tools/apply_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/rollback_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            print(f"removed {rel}")
    print("config.py 30O fields were not automatically removed; restore from git if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
