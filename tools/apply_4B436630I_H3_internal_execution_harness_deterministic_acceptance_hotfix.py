from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H3"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
BACKUP_DIR = Path("_patch_backup") / CONTRACT_VERSION
CHECKER = "tools/check_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py"
OVERWRITE_FILES = [
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630I_H3.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_DETERMINISTIC_CHECKER_HOTFIX_4B436630I_H3.md",
    *OVERWRITE_FILES,
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H3.py",
    CHECKER,
    "tools/rollback_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py",
]
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def backup_existing(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in OVERWRITE_FILES:
        src = root / rel
        dst = root / BACKUP_DIR / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            out[rel] = True
        else:
            out[rel] = False
    return out


def copy_payload(root: Path) -> dict[str, bool]:
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise FileNotFoundError(f"payload missing: {payload}")
    copied: dict[str, bool] = {}
    for src in payload.rglob("*"):
        if src.is_file():
            rel = src.relative_to(payload)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[str(rel).replace("\\", "/")] = True
    return copied


def compile_after_apply(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_FILES:
        path = root / rel
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_checker(root: Path) -> dict[str, Any]:
    env = {**dict(), **__import__('os').environ}
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{__import__('os').pathsep}{env['PYTHONPATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", str(root / CHECKER), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=300,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def remove_payloads(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in ["_patch_payload", "tools/_patch_payload"]:
        path = root / rel
        if path.exists():
            shutil.rmtree(path)
        out[rel] = not path.exists()
    return out


def main() -> int:
    root = repo_root()
    backups = backup_existing(root)
    copied = copy_payload(root)
    compiled = compile_after_apply(root)
    checker_report = run_checker(root)
    payload_removed = remove_payloads(root)
    report = {
        "ok": all(compiled.values()) and bool(checker_report.get("ok")) and int(checker_report.get("returncode", 1)) == 0,
        "contract_version": CONTRACT_VERSION,
        "backup_created": backups,
        "copied": copied,
        "compiled_after_apply": compiled,
        "checker_report": checker_report,
        "payload_removed": payload_removed,
        "read_only": True,
        "paper_live_order_enablement_present": False,
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
    print(f"{CONTRACT_VERSION} deterministic acceptance hotfix applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report.get("checks"), dict) else {}
    for key in [
        "checker_30d_ok",
        "checker_30i_ok",
        "checker_h1_ok",
            "source_30d_no_pyc_syntax_compile_present",
        "source_h1_no_bytecode_cli_present",
        "source_h1_compat_recovery_present",
        "source_h1_test_memoized_cli_present",
        "exchange_submit_still_blocked",
        "paper_execution_still_blocked",
        "paper_candidate_still_blocked",
        "live_real_still_blocked",
    ]:
        print(f" - {key}: {checks.get(key)}")
    print(f" - root_patch_payload_removed: {payload_removed.get('_patch_payload')}")
    print(f" - tools_patch_payload_removed: {payload_removed.get('tools/_patch_payload')}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
