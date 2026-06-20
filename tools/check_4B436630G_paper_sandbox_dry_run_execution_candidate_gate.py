from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30G"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.30F"
EXPECTED_FILES = [
    "README_APPLY_4B436630G.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_4B436630G.md",
    "src/tradebot/paper_sandbox_dry_run_execution_candidate_gate.py",
    "tests/test_paper_sandbox_dry_run_execution_candidate_gate_4B436630G.py",
    "tools/apply_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/check_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/rollback_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/run_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
]
BASE_FILES = [
    "src/tradebot/paper_sandbox_dry_run_transition_plan.py",
    "tools/check_4B436630F_paper_sandbox_dry_run_transition_plan.py",
    "tools/run_4B436630F_paper_sandbox_dry_run_transition_plan.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_execution_candidate_gate_enabled",
    "paper_sandbox_dry_run_execution_candidate_consume_30f_plan_required",
    "paper_sandbox_dry_run_single_simulated_intent_required",
    "paper_sandbox_dry_run_no_exchange_submit_required",
    "paper_sandbox_dry_run_paper_candidate_still_blocked_required",
]
PY_FILES = [item for item in [*EXPECTED_FILES, *BASE_FILES] if item.endswith(".py")]


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


def run_base_30f_checker(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630F_paper_sandbox_dry_run_transition_plan.py"
    if not checker.exists():
        return {"ok": False, "reason": "BASE_30F_CHECKER_MISSING"}
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


def fake_30f_ready() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30F",
        "decision": "PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_transition_plan": True,
        "approved_for_paper_sandbox_dry_run_execution_plan": True,
        "approved_for_order_path_simulation_envelope": True,
        "approved_for_operator_final_go_no_go_checklist": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "order_path_simulation_envelope": {
            "runtime_envelope": "sandbox_only",
            "execution_mode": "dry_run",
            "market_type": "spot_demo",
            "base_url": "https://demo-api.binance.com",
            "auto_trade_on_signal": False,
            "live_trading_armed": False,
            "live_real_double_confirm": False,
            "order_notional_usd": 25.0,
            "order_notional_cap_usd": 25.0,
            "max_open_orders": 1,
        },
    }


def run_module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_execution_candidate_gate import (
        READY_DECISION,
        SOURCE_30F_REQUIRED_DECISION,
        build_from_latest_30f_ready_report,
        build_paper_sandbox_dry_run_execution_candidate_gate_snapshot,
        write_report_bundle,
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        default_payload = build_from_latest_30f_ready_report(reports_dir=temp_dir)
    ready_payload = build_paper_sandbox_dry_run_execution_candidate_gate_snapshot(Settings(), fake_30f_ready())
    with tempfile.TemporaryDirectory() as temp_dir:
        first, _ = write_report_bundle(ready_payload, temp_dir)
        second, _ = write_report_bundle(ready_payload, temp_dir)
        collision_guard_ok = first != second and first.exists() and second.exists()
    return {
        "ok": (
            default_payload.get("decision") == SOURCE_30F_REQUIRED_DECISION
            and ready_payload.get("decision") == READY_DECISION
            and ready_payload.get("approved_for_paper_sandbox_dry_run_execution_candidate_gate") is True
            and ready_payload.get("approved_for_paper_sandbox_dry_run_execution_candidate") is True
            and ready_payload.get("approved_for_single_simulated_paper_intent") is True
            and ready_payload.get("approved_for_no_exchange_submit_verification") is True
            and ready_payload.get("approved_for_paper_sandbox_dry_run_execution") is False
            and ready_payload.get("approved_for_exchange_submit") is False
            and ready_payload.get("approved_for_paper_candidate") is False
            and ready_payload.get("approved_for_live_real") is False
            and ready_payload.get("trading_action_performed") is False
            and ready_payload.get("order_actions_performed") is False
            and collision_guard_ok
        ),
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "ready_candidate_gate": ready_payload.get("approved_for_paper_sandbox_dry_run_execution_candidate_gate"),
        "approved_dry_run_execution": ready_payload.get("approved_for_paper_sandbox_dry_run_execution"),
        "approved_exchange_submit": ready_payload.get("approved_for_exchange_submit"),
        "approved_paper_candidate": ready_payload.get("approved_for_paper_candidate"),
        "approved_live_real": ready_payload.get("approved_for_live_real"),
        "order_actions_blocked": ready_payload.get("order_actions_performed") is False,
        "collision_guard_ok": collision_guard_ok,
    }


def run_check(root: Path) -> dict[str, Any]:
    compiled = compile_py(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    base_files = {rel: (root / rel).exists() for rel in BASE_FILES}
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "config.py").exists() else ""
    config_fields = {field: (field in config_text) for field in CONFIG_FIELDS}
    module_text = (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_candidate_gate.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_candidate_gate.py").exists() else ""
    base_report = run_base_30f_checker(root)
    try:
        probe = run_module_probe(root)
    except Exception as exc:
        probe = {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_base_files_present": all(base_files.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": f'CONTRACT_VERSION = "{CONTRACT_VERSION}"' in module_text,
        "config_30g_fields_present": all(config_fields.values()),
        "base_30f_checker_ok": bool(base_report.get("ok")) and int(base_report.get("returncode", 1)) == 0,
        "source_30f_plan_gate_present": "source_30f_plan_gate" in module_text,
        "dry_run_only_runtime_envelope_gate_present": "dry_run_only_runtime_envelope_gate" in module_text,
        "single_simulated_paper_intent_gate_present": "single_simulated_paper_intent_gate" in module_text,
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in module_text,
        "paper_candidate_still_blocked_gate_present": "paper_candidate_still_blocked_gate" in module_text,
        "report_collision_guard_present": "_unique_report_path" in module_text,
        "module_probe_ok": bool(probe.get("ok")),
        "paper_dry_run_execution_still_blocked": probe.get("approved_dry_run_execution") is False,
        "exchange_submit_still_blocked": probe.get("approved_exchange_submit") is False,
        "paper_candidate_still_blocked": probe.get("approved_paper_candidate") is False,
        "live_real_still_blocked": probe.get("approved_live_real") is False,
        "order_actions_blocked": probe.get("order_actions_blocked") is True,
    }
    report: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()),
        "checks": checks,
        "expected_files": expected,
        "base_files": base_files,
        "config_fields": config_fields,
        "compiled": compiled,
        "base_30f_report": base_report,
        "module_probe": probe,
        "read_only": True,
        "paper_sandbox_dry_run_execution_candidate_gate": True,
        "paper_live_order_enablement_present": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    report = run_check(root)
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} paper sandbox dry-run execution candidate gate check")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
