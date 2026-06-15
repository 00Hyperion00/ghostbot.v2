from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "tools" / "_patch_backup_4B436628F_H3"
TARGETS = [
    ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py",
    ROOT / "src" / "tradebot" / "operator_cockpit_v2_desktop_wrapper.py",
]


def main() -> int:
    restored: list[str] = []
    for target in TARGETS:
        backup = BACKUP_DIR / target.name
        if backup.exists():
            shutil.copy2(backup, target)
            restored.append(str(target.relative_to(ROOT)))
    print("4B.4.3.6.6.28F-H3 rollback completed")
    for item in restored:
        print(f" - restored: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
