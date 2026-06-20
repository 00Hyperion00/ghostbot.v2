from __future__ import annotations

import json
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30I-H4"
FILES_TO_REMOVE = (
    "README_APPLY_4B436630I_H4.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_REPO_HYGIENE_CLEANUP_4B436630I_H4.md",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H4.py",
    "tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py",
    "tools/rollback_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py",
)


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    removed: dict[str, bool] = {}
    for rel in FILES_TO_REMOVE:
        path = root / rel
        if path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    result = {
        "contract_version": CONTRACT_VERSION,
        "removed": removed,
        "ok": all(removed.values()),
        "note": "Rollback removes only 30I-H4 files. It intentionally does not restore tracked _patch_backup artifacts.",
        "exchange_submit_performed": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
