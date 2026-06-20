from __future__ import annotations

import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30I-H2"
BACKUP_DIR = Path("_patch_backup") / CONTRACT_VERSION
RESTORE_FILES = [
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
]
NEW_FILES = [
    "README_APPLY_4B436630I_H2.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_PYTEST_COMPAT_HOTFIX_4B436630I_H2.md",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H2.py",
    "tools/check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
    "tools/rollback_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    for rel in RESTORE_FILES:
        backup = root / BACKUP_DIR / rel
        target = root / rel
        if backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
    for rel in NEW_FILES:
        path = root / rel
        if path.exists():
            path.unlink()
    print(f"{CONTRACT_VERSION} rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
