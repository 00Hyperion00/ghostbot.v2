from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30H"
EXPECTED_FILES = [
    "README_APPLY_4B436630H.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_4B436630H.md",
    "src/tradebot/paper_sandbox_dry_run_execution_readiness_lock.py",
    "tests/test_paper_sandbox_dry_run_execution_readiness_lock_4B436630H.py",
    "tools/apply_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/rollback_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/run_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
]
BASE_FILES = [
    "src/tradebot/paper_sandbox_dry_run_transition_plan.py",
    "src/tradebot/paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/check_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/run_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py",
]
PY_FILES = [item for item in [*EXPECTED_FILES, *BASE_FILES] if item.endswith(".py")]
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_execution_readiness_lock_enabled",
    "paper_sandbox_dry_run_execution_readiness_lock_consume_30g_required",
    "paper_sandbox_dry_run_operator_explicit_lock_required",
    "paper_sandbox_dry_run_operator_lock_operator_id",
    "paper_sandbox_dry_run_operator_lock_phrase",
    "paper_sandbox_dry_run_operator_lock_token",
    "paper_sandbox_dry_run_operator_lock_issued",
    "paper_sandbox_dry_run_operator_lock_issued_at_ms",
    "paper_sandbox_dry_run_operator_lock_ttl_sec",
    "paper_sandbox_dry_run_exchange_submit_hard_block_audit_required",
    "paper_sandbox_dry_run_execution_still_disabled_required",
]
NOW_MS = 1_800_000_000_000


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


def run_base_30g_checker(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py"
    if not checker.exists():
        return {"ok": False, "reason": "BASE_30G_CHECKER_MISSING"}
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


def synthetic_30g_ready_report() -> dict[str, Any]:
    return {
        "ok": True,
        "contract_version": "4B.4.3.6.6.30G",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_READY_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_execution_candidate_gate": True,
        "approved_for_paper_sandbox_dry_run_execution_candidate": True,
        "approved_for_single_simulated_paper_intent": True,
        "approved_for_no_exchange_submit_verification": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "exchange_submit_performed": False,
        "no_exchange_submit": {
            "ok": True,
            "submitted_to_exchange": False,
            "exchange_submit_performed": False,
            "network_submit_attempted": False,
            "exchange_order_id": None,
            "exchange_client_order_id": None,
        },
        "single_simulated_paper_intent": {
            "ok": True,
            "intent_count": 1,
            "submitted_to_exchange": False,
            "symbol": "ETHUSDT",
            "side": "BUY",
            "quote_notional_usd": 25.0,
        },
    }


def module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_execution_readiness_lock import (
        OPERATOR_LOCK_REQUIRED_DECISION,
        READY_DECISION,
        build_operator_lock_settings,
        build_paper_sandbox_dry_run_execution_readiness_lock_snapshot,
        write_report_bundle,
    )
    source = synthetic_30g_ready_report()
    default_payload = build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(Settings(), source, now_ms=NOW_MS)
    ready_settings = build_operator_lock_settings(
        operator_id="operator-30h",
        lock_token="LOCK_PAPER_SANDBOX_DRY_RUN_READINESS",
        issue_lock=True,
        issued_at_ms=NOW_MS,
        ttl_sec=900,
    )
    ready_payload = build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(ready_settings, source, now_ms=NOW_MS)
    with tempfile.TemporaryDirectory() as temp_dir:
        first_json, _ = write_report_bundle(default_payload, temp_dir)
        second_json, _ = write_report_bundle(ready_payload, temp_dir)
        third_json, _ = write_report_bundle(ready_payload, temp_dir)
        collision_guard_ok = first_json != second_json and second_json != third_json and second_json.exists() and third_json.exists()
    return {
        "ok": (
            default_payload.get("decision") == OPERATOR_LOCK_REQUIRED_DECISION
            and ready_payload.get("decision") == READY_DECISION
            and ready_payload.get("approved_for_paper_sandbox_dry_run_execution_readiness_lock") is True
            and ready_payload.get("approved_for_paper_sandbox_dry_run_execution") is False
            and ready_payload.get("approved_for_exchange_submit") is False
            and ready_payload.get("approved_for_paper_candidate") is False
            and ready_payload.get("approved_for_live_real") is False
            and ready_payload.get("exchange_submit_performed") is False
            and collision_guard_ok
        ),
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "ready_lock_only": ready_payload.get("approved_for_paper_sandbox_dry_run_execution_readiness_lock"),
        "approved_execution": ready_payload.get("approved_for_paper_sandbox_dry_run_execution"),
        "approved_exchange_submit": ready_payload.get("approved_for_exchange_submit"),
        "approved_paper_candidate": ready_payload.get("approved_for_paper_candidate"),
        "approved_live_real": ready_payload.get("approved_for_live_real"),
        "exchange_submit_performed": ready_payload.get("exchange_submit_performed"),
        "collision_guard_ok": collision_guard_ok,
    }


def run_check(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    base_files = {rel: (root / rel).exists() for rel in BASE_FILES}
    compiled = compile_py(root)
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "config.py").exists() else ""
    config_fields = {field: field in config_text for field in CONFIG_FIELDS}
    base_30g = run_base_30g_checker(root)
    try:
        probe = module_probe(root)
    except Exception as exc:
        probe = {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_base_files_present": all(base_files.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").exists() else False,
        "config_30h_fields_present": all(config_fields.values()),
        "base_30g_checker_ok": bool(base_30g.get("ok")) and int(base_30g.get("returncode", 0)) == 0,
        "source_30g_candidate_gate_present": "source_30g_candidate_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").exists() else False,
        "operator_explicit_dry_run_lock_gate_present": "operator_explicit_dry_run_lock_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").exists() else False,
        "exchange_submit_hard_block_audit_gate_present": "exchange_submit_hard_block_audit_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").exists() else False,
        "paper_execution_still_disabled_gate_present": "paper_execution_still_disabled_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").exists() else False,
        "report_collision_guard_present": "_unique_report_path" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_execution_readiness_lock.py").exists() else False,
        "module_probe_ok": bool(probe.get("ok")),
        "paper_execution_still_disabled": probe.get("approved_execution") is False,
        "exchange_submit_still_blocked": probe.get("approved_exchange_submit") is False and probe.get("exchange_submit_performed") is False,
        "paper_candidate_still_blocked": probe.get("approved_paper_candidate") is False,
        "live_real_still_blocked": probe.get("approved_live_real") is False,
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()),
        "checks": checks,
        "expected_files": expected,
        "base_files": base_files,
        "compiled": compiled,
        "config_fields": config_fields,
        "base_30g_report": base_30g,
        "module_probe": probe,
        "read_only": True,
        "paper_live_order_enablement_present": False,
        "order_actions_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = run_check(repo_root())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not args.once_json:
        for key, value in report.get("checks", {}).items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
