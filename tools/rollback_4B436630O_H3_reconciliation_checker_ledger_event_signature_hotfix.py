from __future__ import annotations

import json
from pathlib import Path

FILES = [
    "README_APPLY_4B436630O_H3.txt",
    "docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_CHECKER_LEDGER_EVENT_SIGNATURE_4B436630O_H3.md",
    "tools/apply_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py",
    "tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py",
    "tools/rollback_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H3.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    removed = {}
    for rel in FILES:
        path = root / rel
        path.unlink(missing_ok=True)
        removed[rel] = not path.exists()
    print(json.dumps({"ok": all(removed.values()), "removed": removed}, indent=2, sort_keys=True))
    return 0 if all(removed.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
