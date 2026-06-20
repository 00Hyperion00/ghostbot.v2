from __future__ import annotations

import json
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30I-H1"
BACKUP_DIR = Path("_patch_backup") / CONTRACT_VERSION
TARGET_RUNNER = Path("tools/run_4B436630D_operator_approval_evidence_capture.py")
REMOVE_FILES = [
    Path("README_APPLY_4B436630I_H1.txt"),
    Path("docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_CHAIN_HOTFIX_4B436630I_H1.md"),
    Path("tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py"),
    Path("tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py"),
    Path("tools/rollback_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py"),
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    restored_runner = False
    backup_runner = root / BACKUP_DIR / TARGET_RUNNER
    if backup_runner.exists():
        dst = root / TARGET_RUNNER
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_runner, dst)
        restored_runner = True
    removed: dict[str, bool] = {}
    for rel in REMOVE_FILES:
        target = root / rel
        if target.exists():
            target.unlink()
            removed[rel.as_posix()] = True
        else:
            removed[rel.as_posix()] = False
    print(json.dumps({"contract_version": CONTRACT_VERSION, "restored_runner": restored_runner, "removed": removed}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
