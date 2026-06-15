from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "tools" / "_patch_backup_4B436628F_H1" / "operator_cockpit_v2_read_only.py"
TARGET = ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"


def main() -> int:
    if not BACKUP.exists():
        print("4B.4.3.6.6.28F-H1 rollback skipped: backup not found")
        return 0
    shutil.copy2(BACKUP, TARGET)
    print("4B.4.3.6.6.28F-H1 Operator Cockpit HYP-006 binding rollback restored operator_cockpit_v2_read_only.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
