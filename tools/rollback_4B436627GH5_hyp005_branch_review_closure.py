from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "tools" / "_patch_backup_4B436627GH5"
CREATED = BACKUP / ".created_files.json"


def main() -> int:
    if not BACKUP.exists():
        print("4B.4.3.6.6.27G-H5 rollback skipped: backup directory missing")
        return 0
    created = json.loads(CREATED.read_text(encoding="utf-8")) if CREATED.exists() else []
    for rel in created:
        target = ROOT / rel
        backup = BACKUP / rel
        if backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
        elif target.exists():
            target.unlink()
    print("4B.4.3.6.6.27G-H5 rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
