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


def test_30o_h1_checker_baseline_compat_ok() -> None:
    root = repo_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    proc = subprocess.run(
        [sys.executable, str(root / "tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py"), "--once-json"],
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
    assert payload["ok"] is True
    assert payload["checks"]["target_30o_checker_ok"] is True
    assert payload["checks"]["target_mismatch_zero"] is True
    assert payload["checks"]["target_sqlite_mirror_ok"] is True
    assert payload["checks"]["target_exchange_submit_blocked"] is True
    assert payload["checks"]["target_live_real_blocked"] is True
