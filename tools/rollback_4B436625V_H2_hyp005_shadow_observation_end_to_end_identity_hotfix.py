from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = PROJECT_ROOT / "tools" / "_patch_backup_4B436625VH2"


def main() -> int:
    if not BACKUP_DIR.exists():
        print(f"25vh2_rollback_error: backup directory missing: {BACKUP_DIR}")
        return 2
    restored = 0
    for source in sorted(
        path
        for path in BACKUP_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ):
        relative = source.relative_to(BACKUP_DIR)
        target = PROJECT_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored += 1
    print("4B.4.3.6.6.25V-H2 end-to-end canonical identity hotfix rolled back")
    print(f" - restored_files: {restored}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
