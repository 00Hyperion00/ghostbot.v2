from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob("_patch_backup_4B436629C_H1_*"), reverse=True)
    if not backups:
        print("No 4B436629C-H1 backup found")
        return 1
    backup = backups[0]
    restored = []
    for src in backup.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            restored.append(str(rel))
    print("4B436629C-H1 rollback restored")
    for item in restored:
        print(f" - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
