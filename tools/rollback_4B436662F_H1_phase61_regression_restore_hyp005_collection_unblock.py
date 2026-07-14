from __future__ import annotations
import json, shutil
from pathlib import Path
PATCH_ID = "4B436662F_H1"

def main() -> int:
    root = Path.cwd()
    backup_root = root / ".patch_backup" / PATCH_ID
    restored = []
    if backup_root.exists():
        for backup in backup_root.glob("*.before_4B436662F_H1"):
            rel = backup.name.split(".before_4B436662F_H1", 1)[0].replace("__", "/")
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(rel)
    print(json.dumps({"ok": True, "patch_id": PATCH_ID, "restored": restored}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
