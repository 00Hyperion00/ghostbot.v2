from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def run_json_tool(rel: str) -> dict[str, Any]:
    root = repo_root()
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
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
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    payload = json.loads(proc.stdout)
    assert payload.get("ok") is True, json.dumps(payload.get("checks", {}), indent=2, sort_keys=True)
    return payload


def test_30l_h2_checker_compat_ok() -> None:
    payload = run_json_tool("tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py")
    checks = payload["checks"]
    assert checks["h1_checker_ok"] is True
    assert checks["target_30l_checker_ok"] is True
    assert checks["h1_explicit_unlock_gate_present"] is True
    assert checks["h1_sandbox_preflight_gate_present"] is True


def test_30l_h2_preserves_candidate_only_unlock() -> None:
    payload = run_json_tool("tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py")
    checks = payload["checks"]
    assert checks["paper_candidate_unlocked_candidate_only"] is True
    assert checks["paper_execution_still_blocked"] is True


def test_30l_h2_keeps_no_exchange_submit_no_live_real() -> None:
    payload = run_json_tool("tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py")
    checks = payload["checks"]
    assert checks["exchange_submit_still_blocked"] is True
    assert checks["live_real_still_blocked"] is True
    assert payload["exchange_submit_performed"] is False
    assert payload["trading_action_performed"] is False
