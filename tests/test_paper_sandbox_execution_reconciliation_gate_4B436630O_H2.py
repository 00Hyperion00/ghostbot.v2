from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def run_json(rel: str) -> dict[str, object]:
    root = repo_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    proc = subprocess.run([sys.executable, str(root / rel), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=300)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True, json.dumps(payload.get("checks", {}), indent=2, sort_keys=True)
    return payload


def test_30o_h2_checker_ok() -> None:
    payload = run_json("tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py")
    checks = payload["checks"]
    assert checks["target_30o_checker_ok"] is True
    assert checks["h1_checker_ok"] is True


def test_30o_h2_preserves_mismatch_zero_sqlite_and_blocks_submit() -> None:
    payload = run_json("tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py")
    checks = payload["checks"]
    assert checks["target_mismatch_zero"] is True
    assert checks["target_sqlite_mirror_ok"] is True
    assert checks["target_exchange_submit_blocked"] is True
    assert checks["target_live_real_blocked"] is True
