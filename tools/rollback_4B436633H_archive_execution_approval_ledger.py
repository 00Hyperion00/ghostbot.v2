from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633H"
PAYLOAD_FILES = ['src/tradebot/archive_execution_approval_ledger.py', 'tools/check_4B436633H_archive_execution_approval_ledger.py', 'tools/run_4B436633H_archive_execution_approval_ledger.py', 'tests/test_archive_execution_approval_ledger_4B436633H.py', 'docs/ARCHIVE_EXECUTION_APPROVAL_LEDGER_4B436633H.md', 'README_APPLY_4B436633H.txt']


def main() -> int:
    repo_root = Path.cwd()
    backup_dirs = sorted((repo_root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"), key=lambda p: p.name, reverse=True)
    restored: list[str] = []
    removed: list[str] = []
    backup_root = backup_dirs[0] if backup_dirs else None
    for rel in PAYLOAD_FILES:
        target = repo_root / rel
        backup = backup_root / rel if backup_root else None
        if backup and backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(rel)
        elif target.exists():
            target.unlink()
            removed.append(rel)
    print(json.dumps({"patch_id": PATCH_ID, "restored_files": restored, "removed_files": removed, "archive_execution_allowed": False, "archive_move_performed": False, "file_delete_performed": False}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
