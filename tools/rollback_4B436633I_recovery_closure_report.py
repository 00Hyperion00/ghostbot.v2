from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633I"
NEW_FILES = [
    "src/tradebot/recovery_closure_report.py",
    "tools/check_4B436633I_recovery_closure_report.py",
    "tools/run_4B436633I_recovery_closure_report.py",
    "tests/test_recovery_closure_report_4B436633I.py",
    "docs/RECOVERY_CLOSURE_REPORT_4B436633I.md",
    "README_APPLY_4B436633I.txt",
]


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"), reverse=True)
    restored: list[str] = []
    removed: list[str] = []
    backup_root = backups[0] if backups else None

    if backup_root:
        for backup_file in backup_root.rglob("*"):
            if not backup_file.is_file():
                continue
            rel = backup_file.relative_to(backup_root)
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, target)
            restored.append(rel.as_posix())

    for rel in NEW_FILES:
        path = root / rel
        if path.exists() and (not backup_root or not (backup_root / rel).exists()):
            path.unlink()
            removed.append(rel)

    print(json.dumps({"patch_id": PATCH_ID, "rollback_performed": True, "backup_root": str(backup_root or ""), "restored_files": restored, "removed_files": removed}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
