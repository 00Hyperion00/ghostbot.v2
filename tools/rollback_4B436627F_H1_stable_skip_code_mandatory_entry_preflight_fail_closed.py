from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = PROJECT_ROOT / "tools" / "_patch_backup_4B436627F_H1"
CREATED_MARKER = BACKUP_DIR / ".created_files.txt"


def main() -> int:
    if not BACKUP_DIR.exists():
        print("4B436627F_H1_rollback_error: backup directory missing")
        return 2
    restored = 0
    for source in sorted(
        path
        for path in BACKUP_DIR.rglob("*")
        if path.is_file()
        and path != CREATED_MARKER
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    ):
        relative = source.relative_to(BACKUP_DIR)
        target = PROJECT_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored += 1
    print("4B.4.3.6.6.27F-H1 stable skip-code / mandatory entry-preflight fail-closed hotfix rolled back")
    print(f" - restored_files: {restored}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
