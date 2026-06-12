from __future__ import annotations

import shutil
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H1-H1"
BACKUP_DIRNAME = "_patch_backup_4B436627GH1H1"
TARGETS = (
    "tools/apply_4B436627GH1_repository_hygiene_cleanup.py",
    "tools/check_4B436627GH1_repository_hygiene_cleanup.py",
    "tools/rollback_4B436627GH1_repository_hygiene_cleanup.py",
    "tests/test_repository_hygiene_cleanup_4B436627GH1.py",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    backup_root = root / "tools" / BACKUP_DIRNAME
    restored = 0
    for relative in TARGETS:
        backup = backup_root / relative
        target = root / relative
        if backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored += 1
    if restored == 0:
        raise RuntimeError("ROLLBACK_BACKUP_NOT_FOUND")
    print(f"{CONTRACT_VERSION} Windows UTF-8 Git-root detection hotfix rollback completed")
    print(f" - restored_files: {restored}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    sys.exit(main())
