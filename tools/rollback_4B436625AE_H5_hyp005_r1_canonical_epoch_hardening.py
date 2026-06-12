from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP = PROJECT_ROOT / "tools" / "_patch_backup_4B436625AEH5"


def main() -> int:
    if not BACKUP.exists():
        print(f"25AE-H5 rollback error: backup directory missing: {BACKUP}")
        return 2
    restored = 0
    for source in sorted(
        path
        for path in BACKUP.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ):
        target = PROJECT_ROOT / source.relative_to(BACKUP)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored += 1
    print("4B.4.3.6.6.25AE-H5 source overlay rolled back")
    print(f" - restored_files: {restored}")
    print(" - scheduler_mutation_performed: False")
    print(" - config_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
