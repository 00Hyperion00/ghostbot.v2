from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633A"
PATCH_FILES = [
    "src/tradebot/project_recovery_baseline.py",
    "tools/run_4B436633A_project_recovery_baseline.py",
    "tools/check_4B436633A_project_recovery_baseline.py",
    "tools/apply_4B436633A_project_recovery_baseline.py",
    "tools/rollback_4B436633A_project_recovery_baseline.py",
    "tests/test_project_recovery_baseline_4B436633A.py",
    "docs/PROJECT_RECOVERY_BASELINE_4B436633A.md",
    "README_APPLY_4B436633A.txt",
]


def main() -> int:
    repo_root = Path.cwd()
    backup_root = repo_root / "_patch_backup" / PATCH_ID
    restored: list[str] = []
    removed: list[str] = []

    backups = sorted(backup_root.glob("*/")) if backup_root.exists() else []
    latest_backup = backups[-1] if backups else None

    for relative in PATCH_FILES:
        target = repo_root / relative
        backup = latest_backup / relative if latest_backup else None
        if backup is not None and backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(relative)
        elif target.exists():
            target.unlink()
            removed.append(relative)

    result = {
        "patch_id": PATCH_ID,
        "rolled_back": True,
        "restored_files": sorted(restored),
        "removed_files": sorted(removed),
        "trading_action_performed": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
