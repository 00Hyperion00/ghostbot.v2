from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633F_H1"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"))
    if not backups:
        print(json.dumps({"rolled_back": False, "reason": "backup_not_found"}, sort_keys=True))
        return 1
    backup = backups[-1]
    restored: list[str] = []
    for path in backup.rglob("*"):
        if path.is_file():
            rel = path.relative_to(backup)
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            restored.append(rel.as_posix())
    print(json.dumps({"rolled_back": True, "backup_root": str(backup.relative_to(root)), "restored_files": restored}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
