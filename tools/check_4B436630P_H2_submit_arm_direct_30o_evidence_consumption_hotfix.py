from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30P-H2"
EXPECTED_FILES = [
    "README_APPLY_4B436630P_H2.txt",
    "docs/PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_H2_4B436630P.md",
    "src/tradebot/paper_sandbox_submit_arm_preflight.py",
    "tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H2.py",
    "tools/apply_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py",
    "tools/check_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py",
]
PY_FILES = [p for p in EXPECTED_FILES if p.endswith('.py')] + ["tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py", "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py"]

def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start

def compile_files(root: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out

def run_json(root: Path, rel: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run([sys.executable, str(root / rel), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload

def module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_submit_arm_preflight import READY_DECISION, build_paper_sandbox_submit_arm_preflight_snapshot
    source = {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "reconciliation": {"mismatch_count": 0, "mismatch_zero": True, "reconciliation_ok": True},
        "sqlite_audit_mirror": {"sqlite_mirror_ok": True, "sqlite_ok": True},
        "source_30n": {"ledger_consumed": True, "ledger_event": {"event_id": "paper-exec-probe"}},
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
    }
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), source)
    return {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "source_30o_ok": bool(payload.get("source_30o_reconciliation_verified")),
        "submit_still_blocked": bool(payload.get("submit_order_still_blocked")),
        "exchange_submit_blocked": payload.get("approved_for_exchange_submit") is False and payload.get("exchange_submit_performed") is False,
        "live_real_blocked": payload.get("approved_for_live_real") is False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = compile_files(root)
    target = run_json(root, "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py")
    h1 = run_json(root, "tools/check_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix.py") if (root / "tools/check_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix.py").exists() else {"ok": False}
    probe = module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "target_30p_checker_ok": bool(target.get("ok")),
        "h1_checker_ok": bool(h1.get("ok")),
        "direct_30o_h6_evidence_consumption_ok": bool(probe.get("source_30o_ok")),
        "module_probe_ready_ok": bool(probe.get("ok")),
        "submit_still_blocked": bool(probe.get("submit_still_blocked")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
    }
    result = {"ok": all(checks.values()), "contract_version": CONTRACT_VERSION, "checks": checks, "expected_files": expected, "compiled": compiled, "module_probe": probe, "target_30p_report_summary": {"ok": bool(target.get("ok")), "checks": target.get("checks", {})}, "h1_report_summary": {"ok": bool(h1.get("ok")), "checks": h1.get("checks", {})}, "read_only": True, "exchange_submit_performed": False, "trading_action_performed": False, "order_actions_performed": False, "runtime_overlay_activation_performed": False, "scheduler_mutation_performed": False, "strategy_parameter_mutation_performed": False, "training_performed": False, "reload_performed": False, "hyp006_strategy_threshold_mutation_performed": False}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
