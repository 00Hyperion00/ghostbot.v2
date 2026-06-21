from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30R"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_FIELDS = [
    "paper_sandbox_canary_reconciliation_enabled",
    "paper_sandbox_canary_reconciliation_consume_30q_required",
    "paper_sandbox_canary_reconciliation_order_intent_required",
    "paper_sandbox_canary_reconciliation_submit_guard_required",
    "paper_sandbox_canary_reconciliation_mismatch_zero_required",
    "paper_sandbox_canary_reconciliation_no_live_real_required",
    "paper_sandbox_canary_reconciliation_order_intent_path",
    "paper_sandbox_canary_reconciliation_expected_fill_count",
    "paper_sandbox_canary_reconciliation_expected_account_delta_usd",
    "paper_sandbox_canary_reconciliation_expected_position_delta_qty",
    "paper_sandbox_canary_reconciliation_expected_fee_usd",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30R paper sandbox canary reconciliation controls
    paper_sandbox_canary_reconciliation_enabled: bool = True
    paper_sandbox_canary_reconciliation_consume_30q_required: bool = True
    paper_sandbox_canary_reconciliation_order_intent_required: bool = True
    paper_sandbox_canary_reconciliation_submit_guard_required: bool = True
    paper_sandbox_canary_reconciliation_mismatch_zero_required: bool = True
    paper_sandbox_canary_reconciliation_no_live_real_required: bool = True
    paper_sandbox_canary_reconciliation_order_intent_path: str = "reports/production_hardening/4B436630Q_single_canary_order_intent.json"
    paper_sandbox_canary_reconciliation_expected_fill_count: int = 0
    paper_sandbox_canary_reconciliation_expected_account_delta_usd: float = 0.0
    paper_sandbox_canary_reconciliation_expected_position_delta_qty: float = 0.0
    paper_sandbox_canary_reconciliation_expected_fee_usd: float = 0.0
"""
EXPECTED_FILES = [
    "README_APPLY_4B436630R.txt",
    "docs/PAPER_SANDBOX_CANARY_RECONCILIATION_4B436630R.md",
    "src/tradebot/paper_sandbox_canary_reconciliation.py",
    "tests/test_paper_sandbox_canary_reconciliation_4B436630R.py",
    "tools/apply_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/check_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/rollback_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/run_4B436630R_paper_sandbox_canary_reconciliation.py",
]
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")] + ["src/tradebot/config.py"]
ARTIFACT_DIRS = ["_patch_payload", "tools/_patch_payload", "_patch_backup", "tools/_patch_backup", "tests/_patch_backup", "docs/_patch_backup"]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def copy_payload(root: Path) -> dict[str, bool]:
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


def patch_config(root: Path) -> dict[str, Any]:
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


def compile_files(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def remove_artifacts(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in ARTIFACT_DIRS:
        path = root / rel
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        removed[rel] = not path.exists()
    return removed


def run_checker(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else f"{src}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run(
        [sys.executable, str(root / "tools/check_4B436630R_paper_sandbox_canary_reconciliation.py"), "--once-json"],
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
    copied = copy_payload(root)
    config_patch = patch_config(root)
    compiled = compile_files(root)
    removed = remove_artifacts(root)
    checker = run_checker(root)
    payload = {
        "ok": bool(checker.get("ok")) and all(item.get("ok") for item in compiled.values()) and not config_patch["after_missing"] and all(removed.values()),
        "contract_version": CONTRACT_VERSION,
        "copied": copied,
        "config_patch": config_patch,
        "compiled": compiled,
        "removed_patch_artifacts_before_check": removed,
        "checker_report": checker,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "network_submit_attempted": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30R paper sandbox canary reconciliation applied")
    for key in ("base_30p_h3_checker_ok", "module_probe_ok", "module_probe_mismatch_zero", "module_probe_submit_guarded", "module_probe_exchange_submit_blocked", "module_probe_live_real_blocked"):
        print(f" - {key}: {checker.get('checks', {}).get(key)}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
