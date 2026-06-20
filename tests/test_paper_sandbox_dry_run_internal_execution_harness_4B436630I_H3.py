from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

CHECKER_PATH = Path("tools/check_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py")


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def run_h3_checker_cli() -> dict[str, Any]:
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
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    payload = json.loads(proc.stdout)
    assert payload.get("ok") is True, json.dumps(payload.get("checks", {}), indent=2, sort_keys=True)
    return payload


def test_30i_h3_deterministic_acceptance_chain_ok() -> None:
    report = run_h3_checker_cli()
    assert report["checks"]["checker_30d_ok"] is True
    assert report["checks"]["checker_30i_ok"] is True
    assert report["checks"]["checker_h1_ok"] is True


def test_30i_h3_no_bytecode_and_compat_sources_present() -> None:
    report = run_h3_checker_cli()
    assert report["checks"]["source_30d_no_pyc_syntax_compile_present"] is True
    assert report["checks"]["source_h1_no_bytecode_cli_present"] is True
    assert report["checks"]["source_h1_compat_recovery_present"] is True
    assert report["checks"]["source_h1_test_memoized_cli_present"] is True


def test_30i_h3_keeps_all_order_paths_blocked() -> None:
    report = run_h3_checker_cli()
    assert report["checks"]["exchange_submit_still_blocked"] is True
    assert report["checks"]["paper_execution_still_blocked"] is True
    assert report["checks"]["paper_candidate_still_blocked"] is True
    assert report["checks"]["live_real_still_blocked"] is True
    assert report["trading_action_performed"] is False
    assert report["exchange_submit_performed"] is False
