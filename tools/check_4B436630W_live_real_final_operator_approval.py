from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30W"
CONFIG_FIELDS = [
    "live_real_final_operator_approval_enabled",
    "live_real_final_consume_30v_required",
    "live_real_final_operator_approval_required",
    "live_real_final_operator_id_required",
    "live_real_final_operator_approval_token",
    "live_real_final_hard_submit_block_required",
    "live_real_final_no_live_order_required",
    "live_real_final_submit_blocked_until_30x",
    "live_real_final_order_action_cap",
    "live_real_final_exchange_submit_cap",
    "live_real_final_network_submit_cap",
    "live_real_final_max_total_notional_usd",
    "live_real_final_runtime_seconds_cap",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630W.txt",
    "docs/LIVE_REAL_FINAL_OPERATOR_APPROVAL_4B436630W.md",
    "src/tradebot/live_real_final_operator_approval.py",
    "tests/test_live_real_final_operator_approval_4B436630W.py",
    "tools/apply_4B436630W_live_real_final_operator_approval.py",
    "tools/check_4B436630W_live_real_final_operator_approval.py",
    "tools/rollback_4B436630W_live_real_final_operator_approval.py",
    "tools/run_4B436630W_live_real_final_operator_approval.py",
]
PY_FILES = [
    "src/tradebot/live_real_final_operator_approval.py",
    "tests/test_live_real_final_operator_approval_4B436630W.py",
    "tools/apply_4B436630W_live_real_final_operator_approval.py",
    "tools/check_4B436630W_live_real_final_operator_approval.py",
    "tools/rollback_4B436630W_live_real_final_operator_approval.py",
    "tools/run_4B436630W_live_real_final_operator_approval.py",
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
        return {"ok": False, "returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def _source_30v() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30V",
        "decision": "LIVE_REAL_PREFLIGHT_GATE_READY_API_ENV_ACCOUNT_AUDIT_HARD_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER",
        "approved_for_live_real_preflight_gate": True,
        "approved_for_live_real_readiness_candidate": True,
        "api_env_capability_audit_verified": True,
        "account_capability_audit_verified": True,
        "hard_live_submit_block_verified": True,
        "no_exchange_submit_verified": True,
        "no_live_real_order_verified": True,
        "order_action_count": 0,
        "exchange_submit_count": 0,
        "network_submit_count": 0,
        "total_notional_usd": 0.0,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "live_real_order_performed": False,
        "live_real_order_submitted": False,
        "live_real_network_submit_attempted": False,
    }


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.live_real_final_operator_approval import APPROVAL_TOKEN, READY_DECISION, OPERATOR_APPROVAL_REQUIRED_DECISION, build_live_real_final_operator_approval_snapshot

    default_payload = build_live_real_final_operator_approval_snapshot(Settings(), _source_30v())
    ready_payload = build_live_real_final_operator_approval_snapshot(
        Settings(),
        _source_30v(),
        operator_id="operator-30w",
        approval_token=APPROVAL_TOKEN,
        issue_final_approval=True,
    )
    return {
        "ok": ready_payload.get("decision") == READY_DECISION and default_payload.get("decision") == OPERATOR_APPROVAL_REQUIRED_DECISION,
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "source_30v_ok": bool(ready_payload.get("source_30v_live_real_preflight_verified")),
        "operator_approval_ok": bool(ready_payload.get("final_operator_approval_verified")),
        "hard_submit_block_ok": bool(ready_payload.get("hard_live_submit_block_verified")),
        "submit_blocked_until_30x": bool(ready_payload.get("live_real_submit_blocked_until_30x")),
        "no_exchange_submit_ok": bool(ready_payload.get("no_exchange_submit_verified")),
        "no_live_real_order_ok": bool(ready_payload.get("no_live_real_order_verified")),
        "approved_for_final_operator_approval": ready_payload.get("approved_for_live_real_final_operator_approval"),
        "approved_for_30x_candidate": ready_payload.get("approved_for_30x_live_real_micro_canary_candidate"),
        "order_action_count": ready_payload.get("order_action_count"),
        "exchange_submit_count": ready_payload.get("exchange_submit_count"),
        "network_submit_count": ready_payload.get("network_submit_count"),
        "exchange_submit_blocked": ready_payload.get("approved_for_exchange_submit") is False and ready_payload.get("exchange_submit_performed") is False,
        "live_real_blocked": ready_payload.get("approved_for_live_real") is False and ready_payload.get("live_real_order_performed") is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_path = root / "src/tradebot/config.py"
    config_text = config_path.read_text(encoding="utf-8", errors="replace") if config_path.exists() else ""
    source_path = root / "src/tradebot/live_real_final_operator_approval.py"
    source_text = source_path.read_text(encoding="utf-8", errors="replace") if source_path.exists() else ""
    base_checker = root / "tools/check_4B436630V_live_real_preflight_gate.py"
    base_report = _run_json_tool(root, "tools/check_4B436630V_live_real_preflight_gate.py") if base_checker.exists() else {"ok": False, "missing": True}
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30w_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30v_checker_ok": bool(base_report.get("ok")),
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_source_30v_ok": bool(probe.get("source_30v_ok")),
        "module_probe_operator_approval_ok": bool(probe.get("operator_approval_ok")),
        "module_probe_hard_submit_block_ok": bool(probe.get("hard_submit_block_ok")),
        "module_probe_submit_blocked_until_30x": bool(probe.get("submit_blocked_until_30x")),
        "module_probe_no_exchange_submit_ok": bool(probe.get("no_exchange_submit_ok")),
        "module_probe_no_live_real_order_ok": bool(probe.get("no_live_real_order_ok")),
        "exchange_submit_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_blocked": bool(probe.get("live_real_blocked")),
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "base_30v_checker": base_report,
        "module_probe": probe,
        "read_only": True,
        "operator_approval_only": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "network_submit_attempted": False,
        "live_real_order_performed": False,
        "live_real_order_submitted": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
