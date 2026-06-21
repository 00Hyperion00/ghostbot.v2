from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30X"
CONFIG_FIELDS = [
    "live_real_micro_canary_enabled",
    "live_real_micro_canary_consume_30w_required",
    "live_real_micro_canary_operator_approval_required",
    "live_real_micro_canary_operator_id_required",
    "live_real_micro_canary_approval_token",
    "live_real_micro_canary_symbol",
    "live_real_micro_canary_side",
    "live_real_micro_canary_order_type",
    "live_real_micro_canary_quantity",
    "live_real_micro_canary_mark_price",
    "live_real_micro_canary_min_notional_usd",
    "live_real_micro_canary_max_notional_usd",
    "live_real_micro_canary_max_total_notional_usd",
    "live_real_micro_canary_single_order_cap",
    "live_real_micro_canary_exchange_submit_cap",
    "live_real_micro_canary_network_submit_cap",
    "live_real_micro_canary_leverage",
    "live_real_micro_canary_max_leverage",
    "live_real_micro_canary_kill_switch_armed",
    "live_real_micro_canary_hard_caps_required",
    "live_real_micro_canary_perform_network_submit",
    "live_real_micro_canary_submit_handoff_mode",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630X.txt",
    "docs/FIRST_LIVE_REAL_MICRO_CANARY_4B436630X.md",
    "src/tradebot/live_real_micro_canary_gate.py",
    "tests/test_live_real_micro_canary_gate_4B436630X.py",
    "tools/apply_4B436630X_live_real_micro_canary_gate.py",
    "tools/check_4B436630X_live_real_micro_canary_gate.py",
    "tools/rollback_4B436630X_live_real_micro_canary_gate.py",
    "tools/run_4B436630X_live_real_micro_canary_gate.py",
]
PY_FILES = [
    "src/tradebot/live_real_micro_canary_gate.py",
    "tests/test_live_real_micro_canary_gate_4B436630X.py",
    "tools/apply_4B436630X_live_real_micro_canary_gate.py",
    "tools/check_4B436630X_live_real_micro_canary_gate.py",
    "tools/rollback_4B436630X_live_real_micro_canary_gate.py",
    "tools/run_4B436630X_live_real_micro_canary_gate.py",
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
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def _module_probe(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    code = """
from tradebot.config import Settings
from tradebot.live_real_micro_canary_gate import APPROVAL_TOKEN, READY_DECISION, build_first_live_real_micro_canary_snapshot
source = {
    'contract_version': '4B.4.3.6.6.30W',
    'decision': 'LIVE_REAL_FINAL_OPERATOR_APPROVAL_READY_FINAL_APPROVAL_CAPTURED_SUBMIT_BLOCKED_UNTIL_30X_NO_LIVE_REAL_ORDER',
    'approved_for_live_real_final_operator_approval': True,
    'approved_for_30x_live_real_micro_canary_candidate': True,
    'final_operator_approval_verified': True,
    'live_real_submit_blocked_until_30x': True,
    'hard_live_submit_block_verified': True,
    'no_exchange_submit_verified': True,
    'no_live_real_order_verified': True,
    'order_action_count': 0,
    'exchange_submit_count': 0,
    'network_submit_count': 0,
    'total_notional_usd': 0.0,
    'approved_for_exchange_submit': False,
    'approved_for_live_real': False,
    'exchange_submit_performed': False,
    'network_submit_attempted': False,
    'trading_action_performed': False,
    'order_actions_performed': False,
    'live_real_order_performed': False,
    'live_real_order_submitted': False,
    'live_real_network_submit_attempted': False,
}
payload = build_first_live_real_micro_canary_snapshot(Settings(), source, operator_id='operator-30x', approval_token=APPROVAL_TOKEN, issue_micro_canary_approval=True, symbol='ETHUSDT', side='BUY', quantity='0.002', mark_price='2500', write_submit_request=False)
import json
print(json.dumps({'ok': payload['decision'] == READY_DECISION, 'decision': payload['decision'], 'approved_for_exchange_submit': payload['approved_for_exchange_submit'], 'network_submit_attempted': payload['network_submit_attempted'], 'live_real_order_performed': payload['live_real_order_performed']}))
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
    base_30w = _run_json_tool(root, "tools/check_4B436630W_live_real_final_operator_approval.py") if (root / "tools/check_4B436630W_live_real_final_operator_approval.py").exists() else {"ok": True, "skipped": True}
    probe = _module_probe(root)
    checks = {
        "expected_files_ok": all(files.values()),
        "config_fields_ok": all(config_fields.values()),
        "py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "base_30w_checker_ok": bool(base_30w.get("ok")),
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_approved_for_exchange_submit": probe.get("approved_for_exchange_submit"),
        "module_probe_network_submit_attempted": probe.get("network_submit_attempted"),
        "module_probe_live_real_order_performed": probe.get("live_real_order_performed"),
    }
    required_true = (
        checks["expected_files_ok"]
        and checks["config_fields_ok"]
        and checks["py_compile_ok"]
        and checks["base_30w_checker_ok"]
        and checks["module_probe_ok"]
        and checks["module_probe_approved_for_exchange_submit"] is True
    )
    required_false = (
        checks["module_probe_network_submit_attempted"] is False
        and checks["module_probe_live_real_order_performed"] is False
    )
    return {
        "ok": bool(required_true and required_false),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "files": files,
        "config_fields": config_fields,
        "compiled": compiled,
        "base_30w_checker": base_30w,
        "module_probe": probe,
        "approved_for_exchange_submit": probe.get("approved_for_exchange_submit") is True,
        "approved_for_live_real": probe.get("approved_for_exchange_submit") is True,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "live_real_order_performed": False,
        "automated_network_submit_disabled": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    report = build_report(root)
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
