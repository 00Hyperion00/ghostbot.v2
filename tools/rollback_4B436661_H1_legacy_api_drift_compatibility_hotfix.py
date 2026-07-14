from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436661_H1"

def _root() -> Path:
    return Path(__file__).resolve().parents[1]

def main() -> int:
    root = _root()
    backup_dir = root / ".patch_backup" / PATCH_ID
    restored: list[str] = []
    if backup_dir.exists():
        for backup in backup_dir.glob("*.before_4B436661_H1"):
            relative = backup.name.removesuffix(".before_4B436661_H1").replace("__", "/")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(relative)
    result = {
        "ok": True,
        "patch_id": PATCH_ID,
        "rollback_performed": bool(restored),
        "restored_files": restored,
        "file_delete_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "paper_submit_enabled_by_patch": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
