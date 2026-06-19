from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob("_patch_backup_4B436629E_H2_*"), reverse=True)
    if not backups:
        print("No 4B436629E-H2 backup found")
        return 1
    backup = backups[0]
    src = backup / "production_readiness_gate.py"
    if src.exists():
        shutil.copy2(src, root / "src/tradebot/production_readiness_gate.py")
        print(f"Restored {src}")
        return 0
    print(f"Backup file missing: {src}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
