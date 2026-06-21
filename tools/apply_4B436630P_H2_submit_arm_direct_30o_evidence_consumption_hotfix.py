from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30P-H2"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
EXPECTED_FILES = [
    "README_APPLY_4B436630P_H2.txt",
    "docs/PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_H2_4B436630P.md",
    "src/tradebot/paper_sandbox_submit_arm_preflight.py",
    "tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H2.py",
    "tools/apply_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py",
    "tools/check_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py",
]
PY_FILES = [p for p in EXPECTED_FILES if p.endswith('.py')]
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
    copied = {}
    for src in payload.rglob("*"):
        if src.is_file() and "__pycache__" not in src.parts and not src.name.endswith((".pyc", ".pyo")):
            rel = src.relative_to(payload)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[rel.as_posix()] = dst.exists()
    return copied

def compile_files(root: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out

def remove_artifacts(root: Path) -> dict[str, bool]:
    out = {}
    for rel in ARTIFACT_DIRS:
        path = root / rel
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        out[rel] = not path.exists()
    return out

def run_checker(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run([sys.executable, str(root / "tools/check_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py"), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload

def main() -> int:
    root = repo_root()
    copied = copy_payload(root)
    compiled = compile_files(root)
    removed = remove_artifacts(root)
    checker = run_checker(root)
    result = {"ok": bool(checker.get("ok")) and all(item.get("ok") for item in compiled.values()) and all(removed.values()), "contract_version": CONTRACT_VERSION, "copied": copied, "compiled": compiled, "removed_patch_artifacts_before_check": removed, "checker_report": checker, "read_only": True, "exchange_submit_performed": False, "trading_action_performed": False, "order_actions_performed": False, "runtime_overlay_activation_performed": False, "scheduler_mutation_performed": False, "strategy_parameter_mutation_performed": False, "training_performed": False, "reload_performed": False, "hyp006_strategy_threshold_mutation_performed": False}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.30P-H2 submit-arm direct 30O evidence consumption hotfix applied")
    checks = checker.get("checks", {}) if isinstance(checker.get("checks"), dict) else {}
    for key in ("target_30p_checker_ok", "h1_checker_ok", "direct_30o_h6_evidence_consumption_ok", "module_probe_ready_ok", "submit_still_blocked", "exchange_submit_still_blocked", "live_real_still_blocked"):
        print(f" - {key}: {checks.get(key)}")
    return 0 if result["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
