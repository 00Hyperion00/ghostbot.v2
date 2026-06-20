from __future__ import annotations

import json
from pathlib import Path

FILES = [
    "README_APPLY_4B436630H.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_4B436630H.md",
    "src/tradebot/paper_sandbox_dry_run_execution_readiness_lock.py",
    "tests/test_paper_sandbox_dry_run_execution_readiness_lock_4B436630H.py",
    "tools/apply_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/run_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed[rel] = True
        else:
            removed[rel] = False
    print(json.dumps({"rollback": "4B.4.3.6.6.30H", "removed": removed}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
