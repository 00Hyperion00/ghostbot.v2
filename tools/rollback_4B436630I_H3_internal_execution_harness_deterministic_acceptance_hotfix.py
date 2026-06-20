from __future__ import annotations

import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30I-H3"
BACKUP_DIR = Path("_patch_backup") / CONTRACT_VERSION
CREATED_FILES = [
    "README_APPLY_4B436630I_H3.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_DETERMINISTIC_CHECKER_HOTFIX_4B436630I_H3.md",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H3.py",
    "tools/check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
    "tools/check_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py",
    "tools/rollback_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py",
]
RESTORE_FILES = [
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
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
        dst = root / rel
        if backup.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, dst)
    for rel in CREATED_FILES:
        path = root / rel
        if path.exists():
            path.unlink()
    print(f"{CONTRACT_VERSION} rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
