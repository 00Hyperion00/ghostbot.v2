from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob("_patch_backup_4B436629C_H2_*"), reverse=True)
    if not backups:
        print("No 4B436629C-H2 backup directory found; nothing to rollback")
        return 0
    backup = backups[0]
    for src in backup.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"restored {rel.as_posix()}")
    print(f"Rolled back 4B436629C-H2 from {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
