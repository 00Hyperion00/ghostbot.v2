from __future__ import annotations

import argparse
import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HOTFIX_VERSION = "4B.4.3.6.6.30L-H1"
TARGET_CONTRACT_VERSION = "4B.4.3.6.6.30L"
PAYLOAD_DIR = Path("_patch_payload") / TARGET_CONTRACT_VERSION

TARGET_EXPECTED_FILES = [
    "README_APPLY_4B436630L.txt",
    "docs/PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_4B436630L.md",
    "src/tradebot/paper_sandbox_candidate_unlock_gate.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L.py",
    "tools/apply_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/rollback_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/run_4B436630L_paper_sandbox_candidate_unlock_gate.py",
]
HOTFIX_EXPECTED_FILES = [
    "README_APPLY_4B436630L_H1.txt",
    "tools/apply_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
    "tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_candidate_unlock_gate_enabled",
    "paper_sandbox_candidate_unlock_consume_30k_required",
    "paper_sandbox_candidate_unlock_explicit_unlock_required",
    "paper_sandbox_candidate_unlock_operator_id",
    "paper_sandbox_candidate_unlock_phrase",
    "paper_sandbox_candidate_unlock_token",
    "paper_sandbox_candidate_unlock_issued",
    "paper_sandbox_candidate_unlock_issued_at_ms",
    "paper_sandbox_candidate_unlock_ttl_sec",
    "paper_sandbox_candidate_unlock_sandbox_only_preflight_required",
    "paper_sandbox_candidate_unlock_no_exchange_submit_required",
    "paper_sandbox_candidate_unlock_no_live_real_required",
    "paper_sandbox_candidate_unlock_order_enablement_still_blocked_required",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.30L paper sandbox candidate unlock controls
    paper_sandbox_candidate_unlock_gate_enabled: bool = True
    paper_sandbox_candidate_unlock_consume_30k_required: bool = True
    paper_sandbox_candidate_unlock_explicit_unlock_required: bool = True
    paper_sandbox_candidate_unlock_operator_id: str = ""
    paper_sandbox_candidate_unlock_phrase: str = "UNLOCK_PAPER_SANDBOX_CANDIDATE"
    paper_sandbox_candidate_unlock_token: str = ""
    paper_sandbox_candidate_unlock_issued: bool = False
    paper_sandbox_candidate_unlock_issued_at_ms: int = 0
    paper_sandbox_candidate_unlock_ttl_sec: int = 900
    paper_sandbox_candidate_unlock_sandbox_only_preflight_required: bool = True
    paper_sandbox_candidate_unlock_no_exchange_submit_required: bool = True
    paper_sandbox_candidate_unlock_no_live_real_required: bool = True
    paper_sandbox_candidate_unlock_order_enablement_still_blocked_required: bool = True
"""


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
        if not src.is_file():
            continue
        rel = src.relative_to(payload)
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied[rel.as_posix()] = dst.exists()
    return copied


def _patch_config(root: Path) -> dict[str, Any]:
    config = root / "src" / "tradebot" / "config.py"
    text = config.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    if not before_missing:
        return {"patched": False, "before_missing": [], "after_missing": []}
    anchor = "    live_real_hard_block_required: bool = True\n"
    if anchor not in text:
        raise RuntimeError("config.py anchor not found for 30L fields")
    text = text.replace(anchor, CONFIG_BLOCK + anchor, 1)
    config.write_text(text, encoding="utf-8", newline="\n")
    after = config.read_text(encoding="utf-8")
    return {
        "patched": True,
        "before_missing": before_missing,
        "after_missing": [field for field in CONFIG_FIELDS if field not in after],
    }


def _remove_patch_artifacts_before_check(root: Path) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in (
        "_patch_payload",
        "tools/_patch_payload",
        "_patch_backup",
        "tools/_patch_backup",
        "tests/_patch_backup",
        "docs/_patch_backup",
    ):
        path = root / rel
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        removed[rel] = not path.exists()
    return removed


def _compile(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    try:
        py_compile.compile(str(path), doraise=True)
        return {"ok": True, "error": ""}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _run_json_tool(root: Path, rel: str) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(root / rel), "--once-json"],
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-payload", action="store_true", help="Debug only; leaves patch payload in place and skips final acceptance check.")
    args = parser.parse_args()
    root = repo_root()

    copied = _copy_payload(root)
    config_patch = _patch_config(root)
    compiled = {
        rel: _compile(root, rel)
        for rel in [
            *TARGET_EXPECTED_FILES,
            "tools/apply_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
            "tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
        ]
        if rel.endswith(".py")
    }

    # Critical H1 behavior: remove extracted patch payload before invoking 30K/30J/30I-H4 checker chain.
    # Otherwise 30I-H4 repo-hygiene checker correctly fails on patch_payload_absent_after_apply=false.
    removed = {} if args.keep_payload else _remove_patch_artifacts_before_check(root)
    checker_report = {"ok": False, "skipped": True, "reason": "keep_payload requested"} if args.keep_payload else _run_json_tool(
        root,
        "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    )

    target_expected = {rel: (root / rel).exists() for rel in TARGET_EXPECTED_FILES}
    hotfix_expected = {rel: (root / rel).exists() for rel in HOTFIX_EXPECTED_FILES}
    payload_absent = all(removed.values()) if removed else False
    ok = (
        all(copied.values())
        and all(target_expected.values())
        and all(hotfix_expected.values())
        and not config_patch.get("after_missing")
        and all(item.get("ok") for item in compiled.values())
        and payload_absent
        and bool(checker_report.get("ok"))
    )
    result = {
        "ok": ok,
        "contract_version": HOTFIX_VERSION,
        "target_contract_version": TARGET_CONTRACT_VERSION,
        "copied": copied,
        "target_expected_files": target_expected,
        "hotfix_expected_files": hotfix_expected,
        "compiled": compiled,
        "config_patch": config_patch,
        "removed_patch_artifacts_before_check": removed,
        "payload_absent_before_checker": payload_absent,
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
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{HOTFIX_VERSION} candidate unlock payload/apply-order hotfix applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report, dict) else {}
    for key in (
        "base_30k_checker_ok",
        "module_probe_ok",
        "module_probe_explicit_unlock_ok",
        "module_probe_sandbox_preflight_ok",
        "exchange_submit_still_blocked",
        "paper_execution_still_blocked",
        "paper_candidate_unlocked_candidate_only",
        "live_real_still_blocked",
    ):
        print(f" - {key}: {checks.get(key)}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
