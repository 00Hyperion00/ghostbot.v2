from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

RUNNER_PATH = Path("tools/run_4B436630D_operator_approval_evidence_capture.py")
H1_CHECKER_PATH = Path("tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py")
_CACHED_REPORT: dict[str, Any] | None = None


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def run_h1_checker_cli() -> dict[str, Any]:
    global _CACHED_REPORT
    if _CACHED_REPORT is not None:
        return _CACHED_REPORT
    root = repo_root()
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", str(root / H1_CHECKER_PATH), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=300,
    )
    payload = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    assert payload.get("ok") is True, json.dumps(payload.get("checks", {}), indent=2, sort_keys=True)
    _CACHED_REPORT = payload
    return payload


def test_30i_h1_repaired_30d_runner_py_compile_ok() -> None:
    root = repo_root()
    source = (root / RUNNER_PATH).read_text(encoding="utf-8")
    compile(source, str(root / RUNNER_PATH), "exec")


def test_30i_h1_acceptance_chain_repaired() -> None:
    report = run_h1_checker_cli()
    assert report["checks"]["base_30d_checker_ok"] is True
    assert report["checks"]["base_30h_checker_ok"] is True
    assert report["checks"]["base_30i_checker_ok"] is True


def test_30i_h1_preserves_30i_ready_baseline() -> None:
    report = run_h1_checker_cli()
    assert report["checks"]["base_30i_accepted_baseline_preserved"] is True
    probe = report["module_probe"]
    assert probe["ready_internal_harness"] is True
    assert probe["ledger_append_ok"] is True


def test_30i_h1_keeps_no_exchange_submit_and_no_live_real() -> None:
    report = run_h1_checker_cli()
    assert report["checks"]["exchange_submit_still_blocked"] is True
    assert report["checks"]["paper_execution_still_blocked"] is True
    assert report["checks"]["paper_candidate_still_blocked"] is True
    assert report["checks"]["live_real_still_blocked"] is True
    assert report["exchange_submit_performed"] is False
    assert report["trading_action_performed"] is False
