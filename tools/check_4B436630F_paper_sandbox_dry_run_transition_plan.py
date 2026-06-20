from __future__ import annotations

import argparse
import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30F"
EXPECTED_FILES = [
    "README_APPLY_4B436630F.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_4B436630F.md",
    "src/tradebot/paper_sandbox_dry_run_transition_plan.py",
    "tests/test_paper_sandbox_dry_run_transition_plan_4B436630F.py",
    "tools/apply_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/check_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/rollback_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/run_4B436630F_paper_sandbox_dry_run_transition_plan.py",
]
BASE_FILES = [
    "src/tradebot/paper_transition_review_rerun.py",
    "src/tradebot/paper_transition_approval_evidence_capture.py",
    "tools/run_4B436630E_paper_transition_review_rerun.py",
]
PY_FILES = [item for item in [*EXPECTED_FILES, *BASE_FILES] if item.endswith(".py")]
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_transition_plan_enabled",
    "paper_sandbox_dry_run_transition_plan_consume_30e_ready_required",
    "paper_sandbox_dry_run_order_path_simulation_required",
    "paper_sandbox_dry_run_operator_go_no_go_required",
    "paper_sandbox_dry_run_still_no_order_enablement_required",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def compile_py(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_FILES:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_base_30e_checker(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630E_paper_transition_review_rerun.py"
    if not checker.exists():
        return {"ok": False, "reason": "BASE_30E_CHECKER_MISSING"}
    proc = subprocess.run(
        [sys.executable, str(checker), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"ok": False, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    payload["returncode"] = proc.returncode
    return payload


def module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_transition_plan import (
        READY_DECISION,
        SOURCE_30E_REQUIRED_DECISION,
        build_from_latest_30e_ready_report,
        build_paper_sandbox_dry_run_transition_plan_snapshot,
        write_report_bundle,
    )
    source = {
        "contract_version": "4B.4.3.6.6.30E",
        "decision": "PAPER_TRANSITION_REVIEW_RERUN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED",
        "approved_for_paper_transition_review_rerun": True,
        "approved_for_paper_transition_candidate_review": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "rerun_30c_snapshot": {"runtime_envelope_freeze": {"runtime_envelope": "sandbox_only", "execution_mode": "dry_run", "market_type": "spot_demo", "base_url": "https://demo-api.binance.com", "auto_trade_on_signal": False, "live_trading_armed": False, "live_real_double_confirm": False, "max_open_orders": 1}},
    }
    missing_dir = root / ".tradebot" / "tmp_30f_missing"
    if missing_dir.exists():
        shutil.rmtree(missing_dir)
    missing = build_from_latest_30e_ready_report(Settings(), missing_dir)
    ready = build_paper_sandbox_dry_run_transition_plan_snapshot(Settings(), source, source_report_path="synthetic_30e_ready.json")
    tmp = root / ".tradebot" / "tmp_30f_report_collision"
    if tmp.exists():
        shutil.rmtree(tmp)
    first, _ = write_report_bundle(ready, tmp)
    second, _ = write_report_bundle(ready, tmp)
    return {
        "ok": missing.get("decision") == SOURCE_30E_REQUIRED_DECISION and ready.get("decision") == READY_DECISION and first != second,
        "default_decision": missing.get("decision"),
        "ready_decision": ready.get("decision"),
        "ready_plan_only": bool(ready.get("approved_for_paper_sandbox_dry_run_transition_plan")),
        "approved_execution": bool(ready.get("approved_for_paper_sandbox_dry_run_execution")),
        "approved_paper_candidate": bool(ready.get("approved_for_paper_candidate")),
        "approved_live_real": bool(ready.get("approved_for_live_real")),
        "order_actions_blocked": not bool(ready.get("trading_action_performed")) and not bool(ready.get("order_actions_performed")),
        "collision_guard_ok": first != second,
    }


def run_check(root: Path) -> dict[str, Any]:
    compiled = compile_py(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    base = {rel: (root / rel).exists() for rel in BASE_FILES}
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "config.py").exists() else ""
    config_fields = {field: field in config_text for field in CONFIG_FIELDS}
    source = (root / "src" / "tradebot" / "paper_sandbox_dry_run_transition_plan.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_transition_plan.py").exists() else ""
    try:
        probe = module_probe(root)
    except Exception as exc:
        probe = {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    base_30e_report = run_base_30e_checker(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_base_files_present": all(base.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source,
        "config_30f_fields_present": all(config_fields.values()),
        "base_30e_checker_ok": bool(base_30e_report.get("ok", False)) if (root / "tools" / "check_4B436630E_paper_transition_review_rerun.py").exists() else True,
        "source_30e_ready_review_gate_present": "source_30e_ready_review_gate" in source,
        "no_order_to_paper_dry_run_execution_plan_gate_present": "no_order_to_paper_dry_run_execution_plan_gate" in source,
        "order_path_simulation_envelope_gate_present": "order_path_simulation_envelope_gate" in source,
        "operator_final_go_no_go_checklist_gate_present": "operator_final_go_no_go_checklist_gate" in source,
        "report_collision_guard_present": "_unique_report_path" in source,
        "module_probe_ok": bool(probe.get("ok", False)),
        "paper_dry_run_execution_still_blocked": not bool(probe.get("approved_execution", True)),
        "paper_candidate_still_blocked": not bool(probe.get("approved_paper_candidate", True)),
        "live_real_still_blocked": not bool(probe.get("approved_live_real", True)),
        "order_actions_blocked": bool(probe.get("order_actions_blocked", False)),
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()),
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "base_files": base,
        "config_fields": config_fields,
        "module_probe": probe,
        "base_30e_report": base_30e_report,
        "read_only": True,
        "paper_live_order_enablement_present": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = run_check(repo_root())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} paper sandbox dry-run transition plan check: {report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
