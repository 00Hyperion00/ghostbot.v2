from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "tools" / "_patch_backup_4B436628F_H2"

RESTORE_FILES = [
    ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py",
    ROOT / "src" / "tradebot" / "operator_cockpit_hyp006_binding.py",
]


def main() -> int:
    restored = 0
    for target in RESTORE_FILES:
        backup = BACKUP_DIR / target.name
        if backup.exists():
            shutil.copy2(backup, target)
            restored += 1
            print(f"restored: {target.relative_to(ROOT)}")
    print(f"4B.4.3.6.6.28F-H2 rollback complete, restored={restored}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
