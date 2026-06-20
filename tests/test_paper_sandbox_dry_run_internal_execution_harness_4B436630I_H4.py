from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

CHECKER_PATH = Path("tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py")


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def run_h4_checker() -> dict[str, Any]:
    root = repo_root()
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", str(root / CHECKER_PATH), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    payload = json.loads(proc.stdout)
    assert payload.get("ok") is True, json.dumps(payload.get("checks", {}), indent=2, sort_keys=True)
    return payload


def test_30i_h4_removes_tracked_patch_backup() -> None:
    report = run_h4_checker()
    assert report["checks"]["tracked_patch_backup_absent"] is True
    assert report["checks"]["filesystem_patch_backup_absent"] is True


def test_30i_h4_preserves_h3_accepted_baseline() -> None:
    report = run_h4_checker()
    assert report["checks"]["h3_checker_ok"] is True
    assert report["checks"]["h3_accepted_baseline_preserved"] is True


def test_30i_h4_keeps_runtime_blocked() -> None:
    report = run_h4_checker()
    assert report["checks"]["exchange_submit_still_blocked"] is True
    assert report["checks"]["order_actions_blocked"] is True
    assert report["checks"]["paper_execution_still_blocked"] is True
    assert report["checks"]["paper_candidate_still_blocked"] is True
    assert report["checks"]["live_real_still_blocked"] is True
    assert report["exchange_submit_performed"] is False
    assert report["trading_action_performed"] is False


def test_30i_h4_gitignore_and_payload_hygiene() -> None:
    report = run_h4_checker()
    assert report["checks"]["gitignore_hygiene_patterns_present"] is True
    assert report["checks"]["patch_payload_absent_after_apply"] is True
