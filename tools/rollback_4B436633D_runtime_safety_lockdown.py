from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633D"
PATCH_VERSION = "4B.4.3.6.6.33D"
PATCH_FILES = ['src/tradebot/runtime_safety_lockdown.py', 'tools/run_4B436633D_runtime_safety_lockdown.py', 'tools/check_4B436633D_runtime_safety_lockdown.py', 'tests/test_runtime_safety_lockdown_4B436633D.py', 'docs/RUNTIME_SAFETY_LOCKDOWN_4B436633D.md', 'README_APPLY_4B436633D.txt']


def newest_backup(root: Path) -> Path | None:
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"), key=lambda p: p.name, reverse=True)
    return backups[0] if backups else None


def main() -> int:
    root = Path.cwd()
    backup = newest_backup(root)
    restored: list[str] = []
    removed: list[str] = []
    if backup is not None:
        for src in backup.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(backup).as_posix()
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            restored.append(rel)
    for rel in PATCH_FILES:
        target = root / rel
        if target.exists() and rel not in restored:
            target.unlink()
            removed.append(rel)
    result = {
        "rolled_back": True,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "backup_used": None if backup is None else str(backup),
        "restored_files": restored,
        "removed_files": removed,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "exchange_submit_performed": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
