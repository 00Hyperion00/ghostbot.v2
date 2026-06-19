from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob("_patch_backup_4B436629C_*"))
    if not backups:
        print("No 4B436629C backup directory found")
        return 2
    backup = backups[-1]
    restored = []
    for rel in ("src/tradebot/persistence.py", "src/tradebot/config.py"):
        src = backup / rel
        dst = root / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            restored.append(rel)
    print("4B436629C rollback restored:")
    for item in restored:
        print(f" - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
