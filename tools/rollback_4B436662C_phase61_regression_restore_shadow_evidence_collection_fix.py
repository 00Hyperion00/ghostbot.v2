from __future__ import annotations

import shutil
from pathlib import Path

PATCH_ID = "4B436662C"
ROOT = Path.cwd()
BACKUP = ROOT / ".patch_backup" / PATCH_ID

def main() -> int:
    restored = []
    if BACKUP.exists():
        for backup in BACKUP.glob("*.before_4B436662C"):
            rel = backup.name.replace(".before_4B436662C", "").replace("__", "/")
            target = ROOT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(str(target))
    print({"patch_id": PATCH_ID, "restored": restored})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
