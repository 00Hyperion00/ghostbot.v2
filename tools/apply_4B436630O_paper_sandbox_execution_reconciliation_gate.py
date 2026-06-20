from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30O"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
EXPECTED_FILES = [
    "README_APPLY_4B436630O.txt",
    "docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_4B436630O.md",
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py",
    "tools/apply_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/rollback_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
]
PY_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py",
    "tools/apply_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/rollback_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
]
CONFIG_FIELDS_BLOCK = """

    # 4B.4.3.6.6.30O paper sandbox execution reconciliation controls
    paper_sandbox_execution_reconciliation_gate_enabled: bool = True
    paper_sandbox_execution_reconciliation_consume_30n_required: bool = True
    paper_sandbox_execution_reconciliation_mismatch_zero_required: bool = True
    paper_sandbox_execution_reconciliation_sqlite_mirror_required: bool = True
    paper_sandbox_execution_reconciliation_sqlite_path: str = "reports/production_hardening/4B436630O_reconciliation_audit_mirror.sqlite"
    paper_sandbox_execution_reconciliation_no_exchange_submit_required: bool = True
    paper_sandbox_execution_reconciliation_no_live_real_required: bool = True
    paper_sandbox_execution_reconciliation_tolerance: float = 1e-09
"""
CONFIG_FIELDS = [
    "paper_sandbox_execution_reconciliation_gate_enabled",
    "paper_sandbox_execution_reconciliation_consume_30n_required",
    "paper_sandbox_execution_reconciliation_mismatch_zero_required",
    "paper_sandbox_execution_reconciliation_sqlite_mirror_required",
    "paper_sandbox_execution_reconciliation_sqlite_path",
    "paper_sandbox_execution_reconciliation_no_exchange_submit_required",
    "paper_sandbox_execution_reconciliation_no_live_real_required",
    "paper_sandbox_execution_reconciliation_tolerance",
]
ARTIFACT_DIRS = [
    "_patch_payload",
    "tools/_patch_payload",
    "_patch_backup",
    "tools/_patch_backup",
    "tests/_patch_backup",
    "docs/_patch_backup",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _copy_payload(root: Path) -> dict[str, bool]:
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise FileNotFoundError(f"payload missing: {payload}")
    copied: dict[str, bool] = {}
    for src in payload.rglob("*"):
        if src.is_file():
            rel = src.relative_to(payload)
            if "__pycache__" in rel.parts or src.suffix == ".pyc":
                continue
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[rel.as_posix()] = dst.exists()
    return copied


def _patch_config(root: Path) -> dict[str, Any]:
    config = root / "src/tradebot/config.py"
    text = config.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    if not before_missing:
        return {"patched": False, "before_missing": [], "after_missing": []}
    marker = "    live_real_hard_block_required: bool = True"
    if marker not in text:
        raise RuntimeError("config insertion marker missing: live_real_hard_block_required")
    text = text.replace(marker, CONFIG_FIELDS_BLOCK + "    live_real_hard_block_required: bool = True", 1)
    config.write_text(text, encoding="utf-8", newline="\n")
    after = config.read_text(encoding="utf-8")
    return {"patched": True, "before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after]}


def _compile(root: Path) -> dict[str, dict[str, Any]]:
    compiled: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            compiled[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            compiled[rel] = {"ok": False, "error": str(exc)}
    return compiled


def _remove_artifacts(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in ARTIFACT_DIRS:
        path = root / rel
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        removed[rel] = not path.exists()
    return removed


def _run_checker(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run(
        [sys.executable, str(root / "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py"), "--once-json"],
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
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def main() -> int:
    root = repo_root()
    copied = _copy_payload(root)
    config_patch = _patch_config(root)
    compiled = _compile(root)
    removed = _remove_artifacts(root)
    checker_report = _run_checker(root)
    payload = {
        "ok": bool(checker_report.get("ok")) and all(item.get("ok") for item in compiled.values()) and all(removed.values()),
        "contract_version": CONTRACT_VERSION,
        "copied": copied,
        "config_patch": config_patch,
        "compiled": compiled,
        "removed_patch_artifacts_before_check": removed,
        "checker_report": checker_report,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30O paper sandbox execution reconciliation gate applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report.get("checks"), dict) else {}
    for key in (
        "base_30n_checker_ok",
        "module_probe_ok",
        "module_probe_source_30n_ok",
        "module_probe_reconciliation_ok",
        "module_probe_mismatch_zero",
        "module_probe_sqlite_ok",
        "exchange_submit_still_blocked",
        "live_real_still_blocked",
    ):
        print(f" - {key}: {checks.get(key)}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
