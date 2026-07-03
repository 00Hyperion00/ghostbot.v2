from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436634E"
FILES = [
    "README_APPLY_4B436634E.txt",
    "docs/TRANSITION_APPROVAL_DRY_RUN_4B436634E.md",
    "src/tradebot/transition_approval_dry_run.py",
    "tests/test_transition_approval_dry_run_4B436634E.py",
    "tools/check_4B436634E_transition_approval_dry_run.py",
    "tools/run_4B436634E_transition_approval_dry_run.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B436634E files")
    parser.add_argument("--backup-root", default="")
    args = parser.parse_args()
    repo = Path.cwd()
    restored: list[str] = []
    removed: list[str] = []
    backup_root = repo / args.backup_root if args.backup_root else None
    for rel in FILES:
        path = repo / rel
        backup = backup_root / rel if backup_root else None
        if backup is not None and backup.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, path)
            restored.append(rel)
        elif path.exists():
            path.unlink()
            removed.append(rel)
    print(json.dumps({"patch_id": PATCH_ID, "restored_files": restored, "removed_files": removed}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
