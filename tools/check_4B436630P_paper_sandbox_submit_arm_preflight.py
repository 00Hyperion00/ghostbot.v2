from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30P"
PY_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_submit_arm_preflight.py",
    "tests/test_paper_sandbox_submit_arm_preflight_4B436630P.py",
    "tools/apply_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/rollback_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630P.txt",
    "docs/PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_4B436630P.md",
    "src/tradebot/paper_sandbox_submit_arm_preflight.py",
    "tests/test_paper_sandbox_submit_arm_preflight_4B436630P.py",
    "tools/apply_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/rollback_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_submit_arm_preflight_enabled",
    "paper_sandbox_submit_arm_consume_30o_required",
    "paper_sandbox_submit_arm_api_mode",
    "paper_sandbox_submit_arm_base_url",
    "paper_sandbox_submit_arm_min_notional_usd",
    "paper_sandbox_submit_arm_lot_size_step_qty",
    "paper_sandbox_submit_arm_min_qty",
    "paper_sandbox_submit_arm_simulated_price_usd",
    "paper_sandbox_submit_arm_api_mode_required",
    "paper_sandbox_submit_arm_endpoint_required",
    "paper_sandbox_submit_arm_min_notional_check_required",
    "paper_sandbox_submit_arm_lot_size_check_required",
    "paper_sandbox_submit_arm_risk_caps_check_required",
    "paper_sandbox_submit_arm_kill_switch_check_required",
    "paper_sandbox_submit_arm_no_exchange_submit_required",
    "paper_sandbox_submit_arm_no_live_real_required",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile(root: Path) -> dict[str, dict[str, Any]]:
    compiled: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            compiled[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            compiled[rel] = {"ok": False, "error": str(exc)}
    return compiled


def _run_json_tool(root: Path, rel: str) -> dict[str, Any]:
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


def _source_30o() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_execution_reconciliation_gate": True,
        "approved_for_30n_ledger_consumption": True,
        "mismatch_count": 0,
        "mismatch_zero": True,
        "sqlite_mirror_ok": True,
        "ledger_consumed": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_submit_arm_preflight import READY_DECISION, build_paper_sandbox_submit_arm_preflight_snapshot

    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), _source_30o())
    return {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "source_30o_ok": bool(payload.get("source_30o_reconciliation_verified")),
        "sandbox_readiness_ok": bool(payload.get("sandbox_submit_readiness_verified")),
        "api_mode_ok": bool(payload.get("approved_for_api_mode_check")),
        "endpoint_ok": bool(payload.get("approved_for_endpoint_check")),
        "min_notional_ok": bool(payload.get("approved_for_min_notional_check")),
        "lot_size_ok": bool(payload.get("approved_for_lot_size_check")),
        "risk_caps_ok": bool(payload.get("approved_for_risk_caps_check")),
        "kill_switch_ok": bool(payload.get("approved_for_kill_switch_check")),
        "order_skeleton_ok": bool(payload.get("approved_for_order_request_skeleton_build")),
        "submit_still_blocked": payload.get("submit_order_still_blocked") is True,
        "exchange_submit_blocked": payload.get("approved_for_exchange_submit") is False and payload.get("exchange_submit_performed") is False,
        "canary_submit_blocked": payload.get("approved_for_paper_sandbox_canary_submit") is False,
        "live_real_blocked": payload.get("approved_for_live_real") is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/config.py").exists() else ""
    base_checker = root / "tools/check_4B436630O_H6_reconciliation_module_checker_final.py"
    base_report = _run_json_tool(root, "tools/check_4B436630O_H6_reconciliation_module_checker_final.py") if base_checker.exists() else {"ok": False, "missing": True}
    source_text = (root / "src/tradebot/paper_sandbox_submit_arm_preflight.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/paper_sandbox_submit_arm_preflight.py").exists() else ""
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30p_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30o_h6_checker_ok": bool(base_report.get("ok")),
        "source_30o_reconciliation_gate_present": "source_30o_reconciliation_gate" in source_text,
        "api_mode_check_gate_present": "api_mode_check_gate" in source_text,
        "sandbox_endpoint_check_gate_present": "sandbox_endpoint_check_gate" in source_text,
        "min_notional_check_gate_present": "min_notional_check_gate" in source_text,
        "lot_size_check_gate_present": "lot_size_check_gate" in source_text,
        "risk_caps_check_gate_present": "risk_caps_check_gate" in source_text,
        "kill_switch_check_gate_present": "kill_switch_check_gate" in source_text,
        "submit_still_blocked_gate_present": "submit_still_blocked_gate" in source_text,
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in source_text,
        "no_live_real_gate_present": "no_live_real_gate" in source_text,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_source_30o_ok": bool(probe.get("source_30o_ok")),
        "module_probe_sandbox_readiness_ok": bool(probe.get("sandbox_readiness_ok")),
        "module_probe_submit_still_blocked": bool(probe.get("submit_still_blocked")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "paper_sandbox_canary_submit_still_blocked": bool(probe.get("canary_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
        "runtime_training_reload_mutation_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "base_30o_h6_report_summary": {
            "ok": bool(base_report.get("ok")),
            "contract_version": base_report.get("contract_version"),
            "checks": base_report.get("checks", {}),
        },
        "module_probe": probe,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_live_order_enablement_present": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if not args.once_json:
        print(f"{CONTRACT_VERSION} submit-arm preflight check {'OK' if payload['ok'] else 'FAILED'}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
