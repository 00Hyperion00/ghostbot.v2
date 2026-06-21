from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = '4B.4.3.6.6.30T'
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_FIELDS = ['paper_soak_evidence_window_enabled', 'paper_soak_evidence_window_consume_30s_required', 'paper_soak_evidence_window_min_cycles_required', 'paper_soak_evidence_window_cycle_count', 'paper_soak_evidence_window_cycle_cap', 'paper_soak_evidence_window_cap_continuity_required', 'paper_soak_evidence_window_kill_switch_required', 'paper_soak_evidence_window_kill_switch_enabled', 'paper_soak_evidence_window_no_exchange_submit_required', 'paper_soak_evidence_window_no_live_real_required', 'paper_soak_evidence_window_order_action_cap', 'paper_soak_evidence_window_exchange_submit_cap', 'paper_soak_evidence_window_network_submit_cap', 'paper_soak_evidence_window_max_notional_usd', 'paper_soak_evidence_window_runtime_seconds_cap']
CONFIG_BLOCK = '\n    # 4B.4.3.6.6.30T paper soak / evidence window controls\n    paper_soak_evidence_window_enabled: bool = True\n    paper_soak_evidence_window_consume_30s_required: bool = True\n    paper_soak_evidence_window_min_cycles_required: int = 3\n    paper_soak_evidence_window_cycle_count: int = 5\n    paper_soak_evidence_window_cycle_cap: int = 10\n    paper_soak_evidence_window_cap_continuity_required: bool = True\n    paper_soak_evidence_window_kill_switch_required: bool = True\n    paper_soak_evidence_window_kill_switch_enabled: bool = True\n    paper_soak_evidence_window_no_exchange_submit_required: bool = True\n    paper_soak_evidence_window_no_live_real_required: bool = True\n    paper_soak_evidence_window_order_action_cap: int = 0\n    paper_soak_evidence_window_exchange_submit_cap: int = 0\n    paper_soak_evidence_window_network_submit_cap: int = 0\n    paper_soak_evidence_window_max_notional_usd: float = 0.0\n    paper_soak_evidence_window_runtime_seconds_cap: int = 90\n'
EXPECTED_FILES = ['README_APPLY_4B436630T.txt', 'docs/PAPER_SOAK_EVIDENCE_WINDOW_4B436630T.md', 'src/tradebot/paper_soak_evidence_window.py', 'tests/test_paper_soak_evidence_window_4B436630T.py', 'tools/apply_4B436630T_paper_soak_evidence_window.py', 'tools/check_4B436630T_paper_soak_evidence_window.py', 'tools/rollback_4B436630T_paper_soak_evidence_window.py', 'tools/run_4B436630T_paper_soak_evidence_window.py']
PY_FILES = ['src/tradebot/paper_soak_evidence_window.py', 'tests/test_paper_soak_evidence_window_4B436630T.py', 'tools/apply_4B436630T_paper_soak_evidence_window.py', 'tools/check_4B436630T_paper_soak_evidence_window.py', 'tools/rollback_4B436630T_paper_soak_evidence_window.py', 'tools/run_4B436630T_paper_soak_evidence_window.py', 'src/tradebot/config.py']
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
        [sys.executable, str(root / "tools/check_4B436630T_paper_soak_evidence_window.py"), "--once-json"],
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
        "network_submit_attempted": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30T paper soak evidence window applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report.get("checks"), dict) else {}
    for key in (
        "base_30s_checker_ok",
        "module_probe_ok",
        "module_probe_source_30s_ok",
        "module_probe_multi_cycle_soak_ok",
        "module_probe_cap_continuity_ok",
        "module_probe_kill_switch_continuity_ok",
        "module_probe_no_exchange_submit_ok",
        "module_probe_no_live_real_ok",
    ):
        print(f" - {key}: {checks.get(key)}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
