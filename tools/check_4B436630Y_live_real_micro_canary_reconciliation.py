from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30Y"
CONFIG_FIELDS = [
    "live_real_micro_canary_reconciliation_enabled",
    "live_real_micro_canary_reconciliation_consume_30x_required",
    "live_real_micro_canary_reconciliation_execution_evidence_required",
    "live_real_micro_canary_reconciliation_fill_status_required",
    "live_real_micro_canary_reconciliation_mismatch_count_required",
    "live_real_micro_canary_reconciliation_quantity_tolerance",
    "live_real_micro_canary_reconciliation_notional_tolerance_usd",
    "live_real_micro_canary_reconciliation_emergency_stop_required",
    "live_real_micro_canary_reconciliation_emergency_stop_armed",
    "live_real_micro_canary_reconciliation_kill_switch_armed",
    "live_real_micro_canary_reconciliation_no_patch_network_submit_required",
    "live_real_micro_canary_reconciliation_further_live_real_submit_blocked",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630Y.txt",
    "docs/LIVE_REAL_MICRO_CANARY_RECONCILIATION_4B436630Y.md",
    "src/tradebot/live_real_micro_canary_reconciliation.py",
    "tests/test_live_real_micro_canary_reconciliation_4B436630Y.py",
    "tools/apply_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/check_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/rollback_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/run_4B436630Y_live_real_micro_canary_reconciliation.py",
]
PY_FILES = [
    "src/tradebot/live_real_micro_canary_reconciliation.py",
    "tests/test_live_real_micro_canary_reconciliation_4B436630Y.py",
    "tools/apply_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/check_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/rollback_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/run_4B436630Y_live_real_micro_canary_reconciliation.py",
    "src/tradebot/config.py",
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
    proc = subprocess.run([sys.executable, str(root / rel), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def _module_probe(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    code = """
from tradebot.config import Settings
from tradebot.live_real_micro_canary_reconciliation import READY_DECISION, build_live_real_micro_canary_reconciliation_snapshot, build_manual_execution_evidence, evaluate_source_30x_submit_request
source = {
    'contract_version': '4B.4.3.6.6.30X',
    'decision': 'FIRST_LIVE_REAL_MICRO_CANARY_GATE_READY_SINGLE_MIN_SIZE_SUBMIT_REQUEST_BUILT_NO_AUTOMATED_NETWORK_SUBMIT',
    'approved_for_first_live_real_micro_canary_gate': True,
    'approved_for_manual_runtime_handoff': True,
    'approved_for_exchange_submit': True,
    'approved_for_live_real': True,
    'automated_network_submit_disabled_verified': True,
    'submit_request_built': True,
    'network_submit_attempted': False,
    'exchange_submit_performed': False,
}
request = {
    'contract_version': '4B.4.3.6.6.30X',
    'symbol': 'ETHUSDT',
    'side': 'BUY',
    'order_type': 'MARKET',
    'quantity': 0.002,
    'mark_price_reference': 2500.0,
    'notional_usd_reference': 5.0,
    'client_order_id': 'tbv2-30x-test',
}
status = evaluate_source_30x_submit_request(source, request)
evidence = build_manual_execution_evidence(status, operator_id='operator-30y', exchange_order_id='EX-30Y-TEST', ledger_event_id='LEDGER-30Y-TEST')
payload = build_live_real_micro_canary_reconciliation_snapshot(Settings(), source, request, evidence)
import json
print(json.dumps({'ok': payload['decision'] == READY_DECISION, 'decision': payload['decision'], 'mismatch_count': payload['mismatch_count'], 'patch_network_submit_attempted': payload['patch_network_submit_attempted'], 'approved_for_additional_exchange_submit': payload['approved_for_additional_exchange_submit']}))
"""
    proc = subprocess.run([sys.executable, "-c", code], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def build_report(root: Path) -> dict[str, Any]:
    files = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8") if (root / "src/tradebot/config.py").exists() else ""
    config_fields = {field: field in config_text for field in CONFIG_FIELDS}
    compiled = _compile(root)
    base_30x = _run_json_tool(root, "tools/check_4B436630X_live_real_micro_canary_gate.py") if (root / "tools/check_4B436630X_live_real_micro_canary_gate.py").exists() else {"ok": True, "skipped": True}
    probe = _module_probe(root)
    checks = {
        "expected_files_ok": all(files.values()),
        "config_fields_ok": all(config_fields.values()),
        "py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "base_30x_checker_ok": bool(base_30x.get("ok")),
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_mismatch_count_zero": probe.get("mismatch_count") == 0,
        "module_probe_patch_network_submit_attempted": probe.get("patch_network_submit_attempted"),
        "module_probe_no_additional_exchange_submit": probe.get("approved_for_additional_exchange_submit") is False,
    }
    return {
        "ok": all(bool(value) for value in checks.values() if isinstance(value, bool)) and probe.get("patch_network_submit_attempted") is False and probe.get("approved_for_additional_exchange_submit") is False,
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "files": files,
        "config_fields": config_fields,
        "compiled": compiled,
        "base_30x_checker": base_30x,
        "module_probe": probe,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "patch_exchange_submit_performed": False,
        "patch_network_submit_attempted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(repo_root())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
