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


def run_json(rel: str) -> dict[str, Any]:
    root = repo_root()
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run([sys.executable, str(root / rel), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=300)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    payload = json.loads(proc.stdout)
    assert payload.get("ok") is True, json.dumps(payload.get("checks", {}), indent=2, sort_keys=True)
    return payload


def test_30o_h5_target_checker_ok() -> None:
    payload = run_json("tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py")
    checks = payload["checks"]
    assert checks["module_probe_mismatch_zero"] is True
    assert checks["module_probe_sqlite_mirror_ok"] is True
    assert checks["exchange_submit_still_blocked"] is True
    assert checks["live_real_still_blocked"] is True


def test_30o_h5_wrapper_chain_ok() -> None:
    payload = run_json("tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py")
    checks = payload["checks"]
    assert checks["h1_checker_ok"] is True
    assert checks["h2_checker_ok"] is True
    assert checks["h3_checker_ok"] is True
    assert checks["h4_checker_ok"] is True


def test_30o_h5_no_exchange_no_live_real() -> None:
    payload = run_json("tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py")
    assert payload["exchange_submit_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["checks"]["target_exchange_submit_blocked"] is True
    assert payload["checks"]["target_live_real_blocked"] is True
