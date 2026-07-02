from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633D_H1"
PATCH_VERSION = "4B.4.3.6.6.33D-H1"
CREATED_FILES = [
    "README_APPLY_4B436633D_H1.txt",
    "docs/RUNTIME_SAFETY_LOCKDOWN_DESTRUCTIVE_ENDPOINT_GUARD_HOTFIX_4B436633D_H1.md",
    "tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py",
    "tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py",
    "tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py",
]


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"))
    if not backups:
        print(json.dumps({"rolled_back": False, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "error": "backup not found"}, ensure_ascii=False, indent=2))
        return 1
    backup_root = backups[-1]
    restored: list[str] = []
    for backup_file in backup_root.rglob("*"):
        if backup_file.is_file():
            relative = backup_file.relative_to(backup_root)
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, destination)
            restored.append(relative.as_posix())
    removed: list[str] = []
    for relative in CREATED_FILES:
        path = root / relative
        if path.exists() and not (backup_root / relative).exists():
            path.unlink()
            removed.append(relative)
    print(json.dumps({"rolled_back": True, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "backup_root": str(backup_root.relative_to(root)), "restored_files": restored, "removed_created_files": removed}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
