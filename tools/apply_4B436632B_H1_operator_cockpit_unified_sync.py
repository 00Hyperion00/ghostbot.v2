from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.32B-H1"
PAYLOAD_DIR = Path("_patch_payload/4B.4.3.6.6.32B-H1")
BACKUP_DIR = Path("_legacy_launchers/4B.4.3.6.6.32B-H1")
LEGACY_LAUNCHERS = ["run_dashboard.bat", "start_dashboard.bat", "start_tradebot.bat"]
PY_FILES = [
    "src/tradebot/operator_cockpit_unified.py",
    "tools/run_operator_cockpit_unified.py",
    "tools/check_4B436632B_H1_operator_cockpit_unified_sync.py",
    "tools/rollback_4B436632B_H1_operator_cockpit_unified_sync.py",
    "tests/test_operator_cockpit_unified_4B436632B_H1.py",
]

REDIRECT_TEMPLATE = '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\necho TradeBot V2 Operator Cockpit unified launcher is now the only supported desktop entrypoint.\r\ncall "%~dp0start_tradebot_v2_operator_cockpit.bat" %*\r\n'

def _copy_payload(root: Path) -> dict[str, bool]:
    if not (root / PAYLOAD_DIR).exists():
        raise FileNotFoundError(f"payload missing: {root / PAYLOAD_DIR}")
    copied: dict[str, bool] = {}
    for src in (root / PAYLOAD_DIR).rglob("*"):
        if src.is_file() and "__pycache__" not in src.parts and not src.name.endswith((".pyc", ".pyo")):
            rel = src.relative_to(root / PAYLOAD_DIR)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[rel.as_posix()] = dst.exists()
    return copied

def _rewrite_legacy_launchers(root: Path) -> dict[str, Any]:
    BACKUP_DIR_ABS = root / BACKUP_DIR
    BACKUP_DIR_ABS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    result: dict[str, Any] = {}
    for name in LEGACY_LAUNCHERS:
        path = root / name
        backup = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="ignore")
            if "start_tradebot_v2_operator_cockpit.bat" not in existing:
                backup_path = BACKUP_DIR_ABS / f"{name}.{stamp}.bak"
                shutil.copy2(path, backup_path)
                backup = backup_path.as_posix()
        path.write_text(REDIRECT_TEMPLATE, encoding="utf-8", newline="")
        result[name] = {
            "redirect_written": "start_tradebot_v2_operator_cockpit.bat" in path.read_text(encoding="utf-8", errors="ignore"),
            "backup": backup,
        }
    return result

def _compile(root: Path) -> dict[str, dict[str, Any]]:
    compiled: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            compiled[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            compiled[rel] = {"ok": False, "error": str(exc)}
    return compiled

def _run_checker(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run(
        [sys.executable, str(root / "tools/check_4B436632B_H1_operator_cockpit_unified_sync.py"), "--once-json"],
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
    root = Path.cwd().resolve()
    copied = _copy_payload(root)
    launchers = _rewrite_legacy_launchers(root)
    compiled = _compile(root)
    checker = _run_checker(root)
    ok = bool(checker.get("ok")) and all(item.get("ok") for item in compiled.values()) and all(item["redirect_written"] for item in launchers.values())
    payload = {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
        "copied": copied,
        "legacy_launchers": launchers,
        "compiled": compiled,
        "checker_report": checker,
        "single_desktop_entrypoint": "start_tradebot_v2_operator_cockpit.bat",
        "old_launchers_replaced_with_redirect": True,
        "approved_for_live_real_order": False,
        "approved_for_second_micro_order": False,
        "patch_network_submit_attempted": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    print("4B.4.3.6.6.32B-H1 Operator Cockpit unified desktop sync applied")
    print(" - single_entrypoint: start_tradebot_v2_operator_cockpit.bat")
    print(f" - checker_ok: {checker.get('ok')}")
    print(" - live_submit: locked")
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
