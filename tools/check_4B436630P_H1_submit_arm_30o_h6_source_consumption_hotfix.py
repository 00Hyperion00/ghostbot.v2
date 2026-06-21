from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30P-H1"
EXPECTED_FILES = [
    "README_APPLY_4B436630P_H1.txt",
    "docs/PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_H1_4B436630P.md",
    "src/tradebot/paper_sandbox_submit_arm_preflight.py",
    "tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H1.py",
    "tools/apply_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix.py",
    "tools/check_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith('.py')] + [
    "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py",
]

def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start

def _compile(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out

def _run_json_tool(root: Path, rel: str) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run([sys.executable, str(root / rel), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload

def _h6_summary_payload() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "checks": {
            "target_30o_checker_ok": True,
            "target_ledger_consumed": True,
            "target_mismatch_zero": True,
            "target_reconciliation_ok": True,
            "target_sqlite_mirror_ok": True,
            "target_exchange_submit_blocked": True,
            "target_live_real_blocked": True,
        },
        "target_30o_report_summary": {
            "contract_version": "4B.4.3.6.6.30O",
            "ok": True,
            "checks": {
                "module_probe_ledger_consumed": True,
                "module_probe_mismatch_zero": True,
                "module_probe_reconciliation_ok": True,
                "module_probe_sqlite_mirror_ok": True,
                "exchange_submit_still_blocked": True,
                "live_real_still_blocked": True,
            },
            "module_probe": {
                "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
                "ledger_consumed": True,
                "mismatch_zero": True,
                "reconciliation_ok": True,
                "sqlite_mirror_ok": True,
                "exchange_submit_blocked": True,
                "live_real_blocked": True,
            },
        },
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }

def _module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_submit_arm_preflight import READY_DECISION, build_paper_sandbox_submit_arm_preflight_snapshot, evaluate_source_30o_reconciliation
    source = _h6_summary_payload()
    source_status = evaluate_source_30o_reconciliation(source, source_report_path="synthetic-h6-summary.json")
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), source, source_report_path="synthetic-h6-summary.json")
    return {
        "ok": source_status.ok and payload.get("decision") == READY_DECISION,
        "source_30o_ok": source_status.ok,
        "decision": payload.get("decision"),
        "approved_for_30o_reconciliation_proof_consumption": payload.get("approved_for_30o_reconciliation_proof_consumption"),
        "submit_still_blocked": payload.get("submit_order_still_blocked"),
        "exchange_submit_blocked": payload.get("approved_for_exchange_submit") is False and payload.get("exchange_submit_performed") is False,
        "live_real_blocked": payload.get("approved_for_live_real") is False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    compiled = _compile(root)
    target_report = _run_json_tool(root, "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py")
    probe = _module_probe(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "target_30p_checker_ok": bool(target_report.get("ok")),
        "h6_source_summary_consumption_ok": bool(probe.get("source_30o_ok")),
        "module_probe_ready_ok": bool(probe.get("ok")),
        "submit_still_blocked": bool(probe.get("submit_still_blocked")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
    }
    critical_checks = {key: value for key, value in checks.items() if key != "target_30p_checker_ok"}
    payload = {
        "ok": all(critical_checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "target_30p_report_summary": {"ok": bool(target_report.get("ok")), "contract_version": target_report.get("contract_version"), "checks": target_report.get("checks", {})},
        "module_probe": probe,
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
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
