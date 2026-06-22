from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.32A"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_FIELDS = [
    "post_freeze_release_candidate_review_enabled",
    "post_freeze_no_live_submit_required",
    "post_freeze_release_candidate_finalization_token",
    "post_freeze_capital_cap_hard_limit_usdt",
    "post_freeze_second_micro_canary_hard_cap_usdt",
]
CONFIG_BLOCK = """
    # 4B.4.3.6.6.32A post-freeze release candidate review controls
    post_freeze_release_candidate_review_enabled: bool = True
    post_freeze_no_live_submit_required: bool = True
    post_freeze_release_candidate_finalization_token: str = "FINALIZE_32A_RELEASE_CANDIDATE_REVIEW"
    post_freeze_capital_cap_hard_limit_usdt: float = 50.0
    post_freeze_second_micro_canary_hard_cap_usdt: float = 10.0
"""
PY_FILES = [
    "src/tradebot/post_freeze_release_candidate_review.py",
    "tests/test_post_freeze_release_candidate_review_4B436632A.py",
    "tools/run_4B436632A_post_freeze_release_candidate_review.py",
    "tools/check_4B436632A_post_freeze_release_candidate_review.py",
    "tools/apply_4B436632A_post_freeze_release_candidate_review.py",
    "tools/rollback_4B436632A_post_freeze_release_candidate_review.py",
    "src/tradebot/config.py",
]
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
    if not path.exists():
        return {"patched": False, "before_missing": CONFIG_FIELDS, "after_missing": CONFIG_FIELDS, "config_missing": True}
    text = path.read_text(encoding="utf-8")
    before_missing = [field for field in CONFIG_FIELDS if field not in text]
    patched = False
    if before_missing:
        anchors = [
            "    release_hygiene_finalization_token: str = \"FINALIZE_31B_RELEASE_HYGIENE_AUDIT\"\n",
            "    release_hygiene_no_further_live_orders_required: bool = True\n",
            "    live_micro_canary_freeze_finalization_token: str = \"FINALIZE_LIVE_MICRO_CANARY_AUDIT\"\n",
        ]
        for anchor in anchors:
            if anchor in text:
                text = text.replace(anchor, anchor + CONFIG_BLOCK, 1)
                path.write_text(text, encoding="utf-8")
                patched = True
                break
        if not patched:
            text = text.rstrip() + "\n" + CONFIG_BLOCK + "\n"
            path.write_text(text, encoding="utf-8")
            patched = True
    after = path.read_text(encoding="utf-8")
    return {"patched": patched, "before_missing": before_missing, "after_missing": [field for field in CONFIG_FIELDS if field not in after], "config_missing": False}


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
        [sys.executable, str(root / "tools/check_4B436632A_post_freeze_release_candidate_review.py"), "--once-json"],
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
        "ok": bool(checker_report.get("ok")) and all(item.get("ok") for item in compiled.values()) and not config_patch.get("after_missing") and all(removed.values()),
        "contract_version": CONTRACT_VERSION,
        "copied": copied,
        "config_patch": config_patch,
        "compiled": compiled,
        "removed_patch_artifacts_before_check": removed,
        "checker_report": checker_report,
        "approved_for_exchange_submit": False,
        "approved_for_live_real_order": False,
        "approved_for_second_micro_canary_order_submit": False,
        "patch_exchange_submit_performed": False,
        "patch_network_submit_attempted": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.32A post-freeze release candidate review tooling applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report.get("checks"), dict) else {}
    for key in ("ready_decision_ok", "source_31b_verified", "capital_cap_confirmed", "live_real_order_false", "patch_network_submit_false"):
        print(f" - {key}: {checks.get(key)}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
