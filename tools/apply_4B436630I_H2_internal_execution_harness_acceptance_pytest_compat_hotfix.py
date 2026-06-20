from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H2"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
BACKUP_DIR = Path("_patch_backup") / CONTRACT_VERSION
RESTORE_OVERWRITES = [
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
]
PAYLOAD_FILES = [
    "README_APPLY_4B436630I_H2.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_PYTEST_COMPAT_HOTFIX_4B436630I_H2.md",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H2.py",
    "tools/check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
    "tools/rollback_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
]
PY_FILES = [rel for rel in PAYLOAD_FILES if rel.endswith(".py")]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def backup_existing(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in RESTORE_OVERWRITES:
        source = root / rel
        target = root / BACKUP_DIR / rel
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            out[rel] = True
        else:
            out[rel] = False
    return out


def copy_payload(root: Path) -> dict[str, bool]:
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise FileNotFoundError(f"payload missing: {payload}")
    copied: dict[str, bool] = {}
    for rel in PAYLOAD_FILES:
        src = payload / rel
        dst = root / rel
        if not src.exists():
            copied[rel] = False
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied[rel] = dst.exists()
    return copied


def compile_payload(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_checker(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py"
    proc = subprocess.run(
        [sys.executable, str(checker), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=360,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {
            "ok": False,
            "reason": "CHECKER_OUTPUT_NOT_JSON",
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    payload["returncode"] = proc.returncode
    return payload


def remove_payload_dirs(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in ("_patch_payload", "tools/_patch_payload"):
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
        removed[rel] = not path.exists()
    return removed


def main() -> int:
    root = repo_root()
    backup = backup_existing(root)
    copied = copy_payload(root)
    compiled = compile_payload(root)
    checker = run_checker(root)
    removed = remove_payload_dirs(root)
    report: dict[str, Any] = {
        "ok": bool(checker.get("ok")) and all(copied.values()) and all(compiled.values()) and all(removed.values()),
        "contract_version": CONTRACT_VERSION,
        "backup_created": backup,
        "copied": copied,
        "compiled_after_apply": compiled,
        "checker_report": checker,
        "payload_removed": removed,
        "read_only": True,
        "exchange_submit_performed": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} internal execution harness acceptance pytest compatibility hotfix applied")
    checks = checker.get("checks") if isinstance(checker.get("checks"), dict) else {}
    for key, value in checks.items():
        print(f" - {key}: {value}")
    print(f" - root_patch_payload_removed: {removed.get('_patch_payload')}")
    print(f" - tools_patch_payload_removed: {removed.get('tools/_patch_payload')}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
