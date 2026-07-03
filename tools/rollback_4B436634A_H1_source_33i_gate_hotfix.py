
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436634A_H1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 34A-H1 from a backup directory.")
    parser.add_argument("--backup-root", required=True)
    args = parser.parse_args()
    root = Path.cwd()
    backup_root = root / args.backup_root
    restored: list[str] = []
    if not backup_root.exists():
        print(json.dumps({"patch_id": PATCH_ID, "rolled_back": False, "error": "backup_root_missing"}, sort_keys=True))
        return 2
    for path in backup_root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(backup_root)
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            restored.append(rel.as_posix())
    print(json.dumps({"patch_id": PATCH_ID, "rolled_back": True, "restored_files": restored}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
