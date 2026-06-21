from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30Q"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_FIELDS = [
    "first_paper_sandbox_canary_submit_gate_enabled",
    "first_paper_sandbox_canary_consume_30p_required",
    "first_paper_sandbox_canary_operator_approval_required",
    "first_paper_sandbox_canary_operator_id",
    "first_paper_sandbox_canary_operator_approval_phrase",
    "first_paper_sandbox_canary_operator_approval_token",
    "first_paper_sandbox_canary_operator_approval_issued",
    "first_paper_sandbox_canary_operator_approval_issued_at_ms",
    "first_paper_sandbox_canary_operator_approval_ttl_sec",
    "first_paper_sandbox_canary_order_intent_required",
    "first_paper_sandbox_canary_submit_guard_required",
    "first_paper_sandbox_canary_no_live_real_required",
    "first_paper_sandbox_canary_quote_notional_usd",
    "first_paper_sandbox_canary_notional_cap_usd",
    "first_paper_sandbox_canary_min_notional_usd",
    "first_paper_sandbox_canary_min_qty",
    "first_paper_sandbox_canary_step_size",
    "first_paper_sandbox_canary_estimated_price_usd",
    "first_paper_sandbox_canary_order_intent_path",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30Q first paper sandbox canary submit gate controls
    first_paper_sandbox_canary_submit_gate_enabled: bool = True
    first_paper_sandbox_canary_consume_30p_required: bool = True
    first_paper_sandbox_canary_operator_approval_required: bool = True
    first_paper_sandbox_canary_operator_id: str = ""
    first_paper_sandbox_canary_operator_approval_phrase: str = "APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE"
    first_paper_sandbox_canary_operator_approval_token: str = ""
    first_paper_sandbox_canary_operator_approval_issued: bool = False
    first_paper_sandbox_canary_operator_approval_issued_at_ms: int = 0
    first_paper_sandbox_canary_operator_approval_ttl_sec: int = 900
    first_paper_sandbox_canary_order_intent_required: bool = True
    first_paper_sandbox_canary_submit_guard_required: bool = True
    first_paper_sandbox_canary_no_live_real_required: bool = True
    first_paper_sandbox_canary_quote_notional_usd: float = 10.0
    first_paper_sandbox_canary_notional_cap_usd: float = 10.0
    first_paper_sandbox_canary_min_notional_usd: float = 5.0
    first_paper_sandbox_canary_min_qty: float = 0.0001
    first_paper_sandbox_canary_step_size: float = 0.0001
    first_paper_sandbox_canary_estimated_price_usd: float = 2500.0
    first_paper_sandbox_canary_order_intent_path: str = "reports/production_hardening/4B436630Q_single_canary_order_intent.json"
"""
EXPECTED_FILES = [
    "README_APPLY_4B436630Q.txt",
    "docs/FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_4B436630Q.md",
    "src/tradebot/first_paper_sandbox_canary_submit_gate.py",
    "tests/test_first_paper_sandbox_canary_submit_gate_4B436630Q.py",
    "tools/apply_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/check_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/rollback_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/run_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
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
        [sys.executable, str(root / "tools/check_4B436630Q_first_paper_sandbox_canary_submit_gate.py"), "--once-json"],
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
    print("4B.4.3.6.6.30Q first paper sandbox canary submit gate applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report.get("checks"), dict) else {}
    for key in (
        "base_30p_h3_checker_ok",
        "module_probe_ok",
        "module_probe_source_30p_ok",
        "module_probe_approval_ok",
        "module_probe_readiness_ok",
        "module_probe_intent_ok",
        "module_probe_submit_guarded",
        "exchange_submit_still_blocked",
        "live_real_still_blocked",
    ):
        print(f" - {key}: {checks.get(key)}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
