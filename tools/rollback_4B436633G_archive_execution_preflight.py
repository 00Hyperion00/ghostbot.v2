from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633G"
WRITTEN_FILES = ['src/tradebot/archive_execution_preflight.py', 'tools/check_4B436633G_archive_execution_preflight.py', 'tools/run_4B436633G_archive_execution_preflight.py', 'tests/test_archive_execution_preflight_4B436633G.py', 'docs/ARCHIVE_EXECUTION_PREFLIGHT_4B436633G.md', 'README_APPLY_4B436633G.txt']


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _repo_root()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"))
    backup_root = backups[-1] if backups else None
    restored: list[str] = []
    removed: list[str] = []
    for rel in WRITTEN_FILES:
        target = root / rel
        backup = backup_root / rel if backup_root else None
        if backup is not None and backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(rel)
        elif target.exists():
            target.unlink()
            removed.append(rel)
    print(json.dumps({
        "rolled_back": True,
        "patch_id": PATCH_ID,
        "backup_root": str(backup_root.relative_to(root)) if backup_root else "",
        "restored_files": restored,
        "removed_files": removed,
        "destructive_cleanup_performed": False,
        "exchange_submit_performed": False,
        "runtime_overlay_activated": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
