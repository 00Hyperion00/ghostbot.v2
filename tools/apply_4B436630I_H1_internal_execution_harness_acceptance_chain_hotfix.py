from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H1"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
BACKUP_DIR = Path("_patch_backup") / CONTRACT_VERSION
TARGET_RUNNER = Path("tools/run_4B436630D_operator_approval_evidence_capture.py")
PAYLOAD_FILES = [
    "README_APPLY_4B436630I_H1.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_CHAIN_HOTFIX_4B436630I_H1.md",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
    "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
    "tools/rollback_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
    "tools/run_4B436630D_operator_approval_evidence_capture.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def copy_payload(root: Path) -> dict[str, Any]:
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise FileNotFoundError(f"payload missing: {payload}")
    backup = root / BACKUP_DIR
    backup.mkdir(parents=True, exist_ok=True)
    replaced_runner_backup = False
    runner = root / TARGET_RUNNER
    if runner.exists():
        backup_target = backup / TARGET_RUNNER
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runner, backup_target)
        replaced_runner_backup = True
    copied: dict[str, bool] = {}
    for rel in PAYLOAD_FILES:
        src = payload / rel
        dst = root / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[rel] = True
        else:
            copied[rel] = False
    shutil.rmtree(root / "_patch_payload", ignore_errors=True)
    shutil.rmtree(root / "tools" / "_patch_payload", ignore_errors=True)
    return {"copied": copied, "runner_backup_created": replaced_runner_backup}


def compile_targets(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PAYLOAD_FILES:
        if not rel.endswith(".py"):
            continue
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_h1_check(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    checker = root / "tools" / "check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py"
    namespace: dict[str, Any] = {}
    code = checker.read_text(encoding="utf-8")
    exec(compile(code, str(checker), "exec"), namespace)
    return namespace["run_check"](root)


def main() -> int:
    root = repo_root()
    copy_result = copy_payload(root)
    compiled = compile_targets(root)
    report = run_h1_check(root)
    report["copy_result"] = copy_result
    report["compiled_after_apply"] = compiled
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30I-H1 internal execution harness acceptance chain hotfix applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - runner_backup_created: {copy_result['runner_backup_created']}")
    print(f" - root_patch_payload_removed: {not (root / '_patch_payload').exists()}")
    print(f" - tools_patch_payload_removed: {not (root / 'tools' / '_patch_payload').exists()}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
