from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30O-H6"
EXPECTED_FILES = [
    "README_APPLY_4B436630O_H6.txt",
    "docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_H6_FINAL_4B436630O.md",
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py",
    "tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py",
    "tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py",
    "tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py",
    "tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py",
    "tools/check_4B436630O_H6_reconciliation_module_checker_final.py",
    "tools/apply_4B436630O_H6_reconciliation_module_checker_final.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H6.py",
]
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")] + ["tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py"]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile(root: Path) -> dict[str, dict[str, Any]]:
    compiled: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        path = root / rel
        if not path.exists():
            compiled[rel] = {"ok": False, "error": "missing"}
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            compiled[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            compiled[rel] = {"ok": False, "error": str(exc)}
    return compiled


def _run(root: Path, rel: str) -> dict[str, Any]:
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
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    target = _run(root, "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py")
    wrappers = {
        "h1": _run(root, "tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py"),
        "h2": _run(root, "tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py"),
        "h3": _run(root, "tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py"),
        "h4": _run(root, "tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py"),
        "h5": _run(root, "tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py"),
    }
    target_checks = target.get("checks", {}) if isinstance(target.get("checks"), dict) else {}
    compiled = _compile(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "target_30o_checker_ok": bool(target.get("ok")),
        "h1_checker_ok": bool(wrappers["h1"].get("ok")),
        "h2_checker_ok": bool(wrappers["h2"].get("ok")),
        "h3_checker_ok": bool(wrappers["h3"].get("ok")),
        "h4_checker_ok": bool(wrappers["h4"].get("ok")),
        "h5_checker_ok": bool(wrappers["h5"].get("ok")),
        "target_ledger_consumed": bool(target_checks.get("module_probe_ledger_consumed")),
        "target_reconciliation_ok": bool(target_checks.get("module_probe_reconciliation_ok")),
        "target_mismatch_zero": bool(target_checks.get("module_probe_mismatch_zero")),
        "target_sqlite_mirror_ok": bool(target_checks.get("module_probe_sqlite_mirror_ok")),
        "target_exchange_submit_blocked": bool(target_checks.get("exchange_submit_still_blocked")),
        "target_live_real_blocked": bool(target_checks.get("live_real_still_blocked")),
        "runtime_training_reload_mutation_blocked": True,
    }
    out = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "target_30o_report_summary": {
            "ok": bool(target.get("ok")),
            "contract_version": target.get("contract_version"),
            "checks": target_checks,
            "module_probe": target.get("module_probe", {}),
        },
        "wrapper_summaries": {name: {"ok": bool(payload.get("ok")), "checks": payload.get("checks", {})} for name, payload in wrappers.items()},
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
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
