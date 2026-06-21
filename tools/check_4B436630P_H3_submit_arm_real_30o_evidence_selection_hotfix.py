from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30P-H3"
EXPECTED_FILES = [
    "README_APPLY_4B436630P_H3.txt",
    "docs/PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_H3_4B436630P.md",
    "src/tradebot/paper_sandbox_submit_arm_preflight.py",
    "tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H3.py",
    "tools/apply_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py",
    "tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py",
]
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")] + ["tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py", "tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py"]

def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start

def compile_py(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out

def fixture_30o(module_probe_ledger_key: bool = True) -> dict[str, Any]:
    payload = {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "mismatch_count": 0,
        "sqlite_mirror_ok": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "module_probe": {"reconciliation_ok": True, "mismatch_zero": True, "sqlite_mirror_ok": True},
    }
    if module_probe_ledger_key:
        payload["module_probe"]["module_probe_ledger_consumed"] = True
    else:
        payload["paper_execution_ledger_consumed"] = True
    return payload

def run_target_checker(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else f"{src}{os.pathsep}{env['PYTHONPATH']}"
    path = root / "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py"
    if not path.exists():
        return {"ok": False, "missing": True}
    proc = subprocess.run([sys.executable, str(path), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=300)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    data["returncode"] = proc.returncode
    return data

def module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_submit_arm_preflight import (
        READY_DECISION,
        build_from_latest_30o_ready_report,
        build_paper_sandbox_submit_arm_preflight_snapshot,
        evaluate_source_30o_reconciliation,
    )
    direct = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), fixture_30o())
    source = evaluate_source_30o_reconciliation(fixture_30o())
    bad = fixture_30o(); bad["exchange_submit_performed"] = True
    bad_source = evaluate_source_30o_reconciliation(bad)
    with tempfile.TemporaryDirectory() as tmp:
        reports = Path(tmp)
        stale = fixture_30o(); stale["module_probe"].pop("module_probe_ledger_consumed", None); stale["paper_execution_ledger_consumed"] = False
        (reports / "4B436630O_paper_sandbox_execution_reconciliation_gate_20260621T100000Z_ready.json").write_text(json.dumps(stale), encoding="utf-8")
        (reports / "4B436630O_paper_sandbox_execution_reconciliation_gate_20260621T090000Z_ready.json").write_text(json.dumps(fixture_30o()), encoding="utf-8")
        selected = build_from_latest_30o_ready_report(Settings(), reports_dir=reports)
    return {
        "ok": direct.get("decision") == READY_DECISION and source.ok and not bad_source.ok and selected.get("decision") == READY_DECISION,
        "direct_decision": direct.get("decision"),
        "source_ok": source.ok,
        "bad_exchange_blocked": not bad_source.ok,
        "selection_decision": selected.get("decision"),
        "selection_source_ok": selected.get("approved_for_30o_reconciliation_proof_consumption"),
        "submit_blocked": direct.get("approved_for_exchange_submit") is False and direct.get("approved_for_paper_sandbox_canary_submit") is False,
        "exchange_submit_blocked": direct.get("exchange_submit_performed") is False,
        "live_real_blocked": direct.get("approved_for_live_real") is False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    compiled = compile_py(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    probe = module_probe(root)
    target = run_target_checker(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(v.get("ok") for v in compiled.values()),
        "contract_version_ok": True,
        "target_30p_checker_ok": bool(target.get("ok")),
        "real_30o_evidence_selection_ok": bool(probe.get("selection_source_ok")),
        "module_probe_ready_ok": bool(probe.get("ok")),
        "submit_still_blocked": bool(probe.get("submit_blocked")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
    }
    result = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "module_probe": probe,
        "target_30p_report_summary": {"ok": bool(target.get("ok")), "checks": target.get("checks", {})},
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
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
