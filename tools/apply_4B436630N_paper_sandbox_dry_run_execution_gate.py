from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30N"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_execution_gate_enabled",
    "paper_sandbox_dry_run_execution_consume_30m_required",
    "paper_sandbox_dry_run_execution_authorization_required",
    "paper_sandbox_dry_run_execution_operator_id",
    "paper_sandbox_dry_run_execution_authorization_phrase",
    "paper_sandbox_dry_run_execution_authorization_token",
    "paper_sandbox_dry_run_execution_authorization_issued",
    "paper_sandbox_dry_run_execution_authorization_issued_at_ms",
    "paper_sandbox_dry_run_execution_authorization_ttl_sec",
    "paper_sandbox_dry_run_execution_ledger_append_required",
    "paper_sandbox_dry_run_execution_ledger_path",
    "paper_sandbox_dry_run_execution_no_exchange_submit_required",
    "paper_sandbox_dry_run_execution_no_live_real_required",
    "paper_sandbox_dry_run_execution_simulated_fill_price_usd",
    "paper_sandbox_dry_run_execution_simulated_fee_bps",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30N paper sandbox dry-run execution gate controls
    paper_sandbox_dry_run_execution_gate_enabled: bool = True
    paper_sandbox_dry_run_execution_consume_30m_required: bool = True
    paper_sandbox_dry_run_execution_authorization_required: bool = True
    paper_sandbox_dry_run_execution_operator_id: str = ""
    paper_sandbox_dry_run_execution_authorization_phrase: str = "AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION"
    paper_sandbox_dry_run_execution_authorization_token: str = ""
    paper_sandbox_dry_run_execution_authorization_issued: bool = False
    paper_sandbox_dry_run_execution_authorization_issued_at_ms: int = 0
    paper_sandbox_dry_run_execution_authorization_ttl_sec: int = 900
    paper_sandbox_dry_run_execution_ledger_append_required: bool = True
    paper_sandbox_dry_run_execution_ledger_path: str = "reports/production_hardening/4B436630N_internal_paper_execution_ledger.jsonl"
    paper_sandbox_dry_run_execution_no_exchange_submit_required: bool = True
    paper_sandbox_dry_run_execution_no_live_real_required: bool = True
    paper_sandbox_dry_run_execution_simulated_fill_price_usd: float = 2500.0
    paper_sandbox_dry_run_execution_simulated_fee_bps: float = 10.0
"""
EXPECTED_FILES = [
    "README_APPLY_4B436630N.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_4B436630N.md",
    "src/tradebot/paper_sandbox_dry_run_execution_gate.py",
    "tests/test_paper_sandbox_dry_run_execution_gate_4B436630N.py",
    "tools/apply_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/rollback_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/run_4B436630N_paper_sandbox_dry_run_execution_gate.py",
]
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")] + ["src/tradebot/config.py"]
ARTIFACT_DIRS = ["_patch_payload", "tools/_patch_payload", "_patch_backup", "tools/_patch_backup", "tests/_patch_backup", "docs/_patch_backup"]


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
        if src.is_file() and "__pycache__" not in src.parts and not src.name.endswith((".pyc", ".pyo")):
            rel = src.relative_to(payload)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[rel.as_posix()] = dst.exists()
    return copied


def _patch_config(root: Path) -> dict[str, Any]:
    path = root / "src/tradebot/config.py"
    text = path.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    patched = False
    if before_missing:
        anchor = "    live_real_hard_block_required: bool = True\n"
        if anchor not in text:
            raise RuntimeError("config anchor live_real_hard_block_required not found")
        text = text.replace(anchor, CONFIG_BLOCK + anchor, 1)
        path.write_text(text, encoding="utf-8")
        patched = True
    after = path.read_text(encoding="utf-8")
    return {"patched": patched, "before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after]}


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
        [sys.executable, str(root / "tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py"), "--once-json"],
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
        "ok": bool(checker_report.get("ok")) and all(item.get("ok") for item in compiled.values()) and not config_patch["after_missing"] and all(removed.values()),
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
    print("4B.4.3.6.6.30N paper sandbox dry-run execution gate applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report.get("checks"), dict) else {}
    for key in (
        "base_30l_h2_checker_ok",
        "module_probe_ok",
        "module_probe_authorization_ok",
        "module_probe_simulation_ok",
        "module_probe_ledger_append_ok",
        "paper_execution_authorized_internal_only",
        "exchange_submit_still_blocked",
        "live_real_still_blocked",
    ):
        print(f" - {key}: {checks.get(key)}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
