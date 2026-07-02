from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633E_H1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _repo_root()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"), reverse=True)
    if not backups:
        print(json.dumps({"rolled_back": False, "reason": "backup_not_found", "patch_id": PATCH_ID}, indent=2, sort_keys=True))
        return 1
    backup = backups[0]
    restored: list[str] = []
    for path in backup.rglob("*"):
        if path.is_file():
            rel = path.relative_to(backup)
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            restored.append(str(rel).replace("\\", "/"))
    print(json.dumps({"rolled_back": True, "patch_id": PATCH_ID, "backup_root": str(backup.relative_to(root)), "restored_files": restored}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
