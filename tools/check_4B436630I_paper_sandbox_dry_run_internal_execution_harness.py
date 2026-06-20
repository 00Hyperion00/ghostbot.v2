from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I"
READY_DECISION = "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_READY_SIMULATED_FILL_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED"
EXPECTED_FILES = [
    "README_APPLY_4B436630I.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_4B436630I.md",
    "src/tradebot/paper_sandbox_dry_run_internal_execution_harness.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I.py",
    "tools/apply_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "tools/rollback_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "tools/run_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
]
BASE_FILES = [
    "src/tradebot/paper_sandbox_dry_run_execution_readiness_lock.py",
    "src/tradebot/paper_sandbox_dry_run_execution_candidate_gate.py",
    "tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "tools/run_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_internal_execution_harness_enabled",
    "paper_sandbox_dry_run_internal_execution_consume_30h_lock_required",
    "paper_sandbox_dry_run_internal_only_harness_required",
    "paper_sandbox_dry_run_simulated_fill_ledger_append_required",
    "paper_sandbox_dry_run_simulated_fill_ledger_path",
    "paper_sandbox_dry_run_internal_no_exchange_submit_required",
    "paper_sandbox_dry_run_internal_paper_candidate_still_blocked_required",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def compile_py(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in [*EXPECTED_FILES, *BASE_FILES]:
        if not rel.endswith(".py"):
            continue
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_base_30h_checker(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py"
    if not checker.exists():
        return {"ok": False, "reason": "BASE_30H_CHECKER_MISSING"}
    proc = subprocess.run(
        [sys.executable, str(checker), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"ok": False, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    payload["returncode"] = proc.returncode
    return payload


def ready_30h_snapshot() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30H",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_READY_PAPER_EXECUTION_DISABLED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_execution_readiness_lock": True,
        "approved_for_paper_sandbox_dry_run_execution_readiness_candidate": True,
        "approved_for_operator_explicit_dry_run_lock": True,
        "approved_for_exchange_submit_hard_block_audit": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_execution_still_disabled_verified": True,
        "exchange_submit_performed": False,
        "paper_order_enablement_still_blocked": True,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_live_order_enablement_present": False,
        "exchange_submit_hard_block_audit": {
            "approved_for_exchange_submit": False,
            "submitted_to_exchange": False,
            "exchange_submit_performed": False,
            "network_submit_attempted": False,
            "exchange_order_id_present": False,
            "exchange_client_order_id_present": False,
        },
        "source_30g_snapshot": {
            "dry_run_only_runtime_envelope": {
                "runtime_envelope": "sandbox_only",
                "execution_mode": "dry_run",
                "market_type": "spot_demo",
                "base_url": "https://demo-api.binance.com",
                "auto_trade_on_signal": False,
                "live_trading_armed": False,
                "live_real_double_confirm": False,
            },
            "single_simulated_paper_intent": {
                "symbol": "ETHUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quote_notional_usd": 25.0,
            },
        },
    }


def run_module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_internal_execution_harness import (
        build_paper_sandbox_dry_run_internal_execution_harness_snapshot,
    )
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "ledger.jsonl"
        default_payload = build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
            Settings(),
            {},
            ledger_path=ledger_path,
            append_ledger=True,
            now_ms=1_800_000_000_000,
        )
        ready_payload = build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
            Settings(),
            ready_30h_snapshot(),
            source_report_path="reports/production_hardening/30h_ready.json",
            ledger_path=ledger_path,
            append_ledger=True,
            now_ms=1_800_000_000_001,
        )
        collision_payload = build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
            Settings(),
            ready_30h_snapshot(),
            source_report_path="reports/production_hardening/30h_ready.json",
            ledger_path=ledger_path,
            append_ledger=True,
            now_ms=1_800_000_000_002,
        )
        ledger_lines = ledger_path.read_text(encoding="utf-8").strip().splitlines() if ledger_path.exists() else []
    return {
        "ok": ready_payload.get("decision") == READY_DECISION and len(ledger_lines) == 2,
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "ready_internal_harness": bool(ready_payload.get("approved_for_paper_sandbox_dry_run_internal_execution_harness", False)),
        "ledger_append_ok": bool(ready_payload.get("simulated_fill_ledger_append_verified", False)) and len(ledger_lines) == 2,
        "collision_append_ok": bool(collision_payload.get("simulated_fill_ledger_append_verified", False)),
        "exchange_submit_blocked": ready_payload.get("approved_for_exchange_submit") is False and ready_payload.get("exchange_submit_performed") is False,
        "paper_execution_blocked": ready_payload.get("approved_for_paper_sandbox_dry_run_execution") is False,
        "paper_candidate_blocked": ready_payload.get("approved_for_paper_candidate") is False,
        "live_real_blocked": ready_payload.get("approved_for_live_real") is False,
        "order_actions_blocked": ready_payload.get("trading_action_performed") is False and ready_payload.get("order_actions_performed") is False,
    }


def run_check(root: Path) -> dict[str, Any]:
    compiled = compile_py(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    base = {rel: (root / rel).exists() for rel in BASE_FILES}
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8")
    config_fields = {field: (field in config_text) for field in CONFIG_FIELDS}
    source_text = (root / "src" / "tradebot" / "paper_sandbox_dry_run_internal_execution_harness.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_internal_execution_harness.py").exists() else ""
    base_report = run_base_30h_checker(root)
    module_probe = run_module_probe(root) if all(expected.values()) and all(compiled.values()) else {"ok": False}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_base_files_present": all(base.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": f'CONTRACT_VERSION = "{CONTRACT_VERSION}"' in source_text,
        "config_30i_fields_present": all(config_fields.values()),
        "base_30h_checker_ok": bool(base_report.get("ok")) and int(base_report.get("returncode", 1)) == 0,
        "source_30h_readiness_lock_gate_present": "source_30h_readiness_lock_gate" in source_text,
        "internal_only_execution_harness_gate_present": "internal_only_execution_harness_gate" in source_text,
        "simulated_fill_ledger_append_gate_present": "simulated_fill_ledger_append_gate" in source_text,
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in source_text,
        "paper_candidate_still_blocked_gate_present": "paper_candidate_still_blocked_gate" in source_text,
        "report_collision_guard_present": "_unique_report_path" in source_text,
        "module_probe_ok": bool(module_probe.get("ok")),
        "ledger_append_ok": bool(module_probe.get("ledger_append_ok")),
        "paper_execution_still_blocked": bool(module_probe.get("paper_execution_blocked")),
        "exchange_submit_still_blocked": bool(module_probe.get("exchange_submit_blocked")),
        "paper_candidate_still_blocked": bool(module_probe.get("paper_candidate_blocked")),
        "live_real_still_blocked": bool(module_probe.get("live_real_blocked")),
        "order_actions_blocked": bool(module_probe.get("order_actions_blocked")),
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "expected_files": expected,
        "base_files": base,
        "compiled": compiled,
        "config_fields": config_fields,
        "base_30h_report": base_report,
        "module_probe": module_probe,
        "checks": checks,
        "read_only": True,
        "paper_live_order_enablement_present": False,
        "exchange_submit_performed": False,
        "order_actions_performed": False,
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
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} paper sandbox dry-run internal execution harness check")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
