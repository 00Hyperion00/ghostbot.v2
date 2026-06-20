from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30L-H2"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
EXPECTED_FILES = [
    "README_APPLY_4B436630L_H2.txt",
    "docs/PAPER_SANDBOX_CANDIDATE_UNLOCK_HOTFIX_CHECKER_COMPAT_4B436630L_H2.md",
    "tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
    "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tools/apply_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tools/rollback_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L_H2.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]
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
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[rel.as_posix()] = dst.exists()
    return copied


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
    env = dict(**__import__("os").environ)
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{__import__('os').pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run(
        [sys.executable, str(root / "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py"), "--once-json"],
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
    compiled = _compile(root)
    removed = _remove_artifacts(root)
    checker_report = _run_checker(root)
    payload = {
        "ok": bool(checker_report.get("ok")) and all(item.get("ok") for item in compiled.values()) and all(removed.values()),
        "contract_version": CONTRACT_VERSION,
        "copied": copied,
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
    print("4B.4.3.6.6.30L-H2 candidate unlock hotfix checker compat applied")
    for key in (
        "h1_checker_ok",
        "target_30l_checker_ok",
        "base_30k_checker_ok",
        "h1_explicit_unlock_gate_present",
        "h1_sandbox_preflight_gate_present",
        "exchange_submit_still_blocked",
        "live_real_still_blocked",
    ):
        print(f" - {key}: {checker_report.get('checks', {}).get(key)}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
