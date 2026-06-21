from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30V"
CONFIG_FIELDS = [
    "live_real_preflight_enabled",
    "live_real_preflight_consume_30u_required",
    "live_real_preflight_capability_audit_required",
    "live_real_preflight_api_env_audit_required",
    "live_real_preflight_account_capability_audit_required",
    "live_real_preflight_api_key_presence_required",
    "live_real_preflight_account_capability_mode",
    "live_real_preflight_hard_submit_block_required",
    "live_real_preflight_no_live_order_required",
    "live_real_preflight_order_action_cap",
    "live_real_preflight_exchange_submit_cap",
    "live_real_preflight_network_submit_cap",
    "live_real_preflight_max_total_notional_usd",
    "live_real_preflight_runtime_seconds_cap",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630V.txt",
    "docs/LIVE_REAL_PREFLIGHT_GATE_4B436630V.md",
    "src/tradebot/live_real_preflight_gate.py",
    "tests/test_live_real_preflight_gate_4B436630V.py",
    "tools/apply_4B436630V_live_real_preflight_gate.py",
    "tools/check_4B436630V_live_real_preflight_gate.py",
    "tools/rollback_4B436630V_live_real_preflight_gate.py",
    "tools/run_4B436630V_live_real_preflight_gate.py",
]
PY_FILES = [
    "src/tradebot/live_real_preflight_gate.py",
    "tests/test_live_real_preflight_gate_4B436630V.py",
    "tools/apply_4B436630V_live_real_preflight_gate.py",
    "tools/check_4B436630V_live_real_preflight_gate.py",
    "tools/rollback_4B436630V_live_real_preflight_gate.py",
    "tools/run_4B436630V_live_real_preflight_gate.py",
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


def _source_30u() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30U",
        "decision": "PAPER_PROMOTION_REVIEW_READY_RISK_ACCEPTANCE_GATES_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_promotion_review": True,
        "approved_for_paper_runtime_promotion_candidate": True,
        "risk_acceptance_gates_verified": True,
        "promotion_readiness_review_verified": True,
        "no_exchange_submit_verified": True,
        "no_live_real_verified": True,
        "soak_cycle_count": 5,
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
    }


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.live_real_preflight_gate import READY_DECISION, build_live_real_preflight_gate_snapshot

    payload = build_live_real_preflight_gate_snapshot(Settings(), _source_30u(), env={})
    return {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "source_30u_ok": bool(payload.get("source_30u_promotion_review_verified")),
        "api_env_capability_audit_ok": bool(payload.get("api_env_capability_audit_verified")),
        "account_capability_audit_ok": bool(payload.get("account_capability_audit_verified")),
        "hard_submit_block_ok": bool(payload.get("hard_live_submit_block_verified")),
        "no_exchange_submit_ok": bool(payload.get("no_exchange_submit_verified")),
        "no_live_real_order_ok": bool(payload.get("no_live_real_order_verified")),
        "approved_for_live_real_preflight_gate": payload.get("approved_for_live_real_preflight_gate"),
        "approved_for_live_real_readiness_candidate": payload.get("approved_for_live_real_readiness_candidate"),
        "order_action_count": payload.get("order_action_count"),
        "exchange_submit_count": payload.get("exchange_submit_count"),
        "network_submit_count": payload.get("network_submit_count"),
        "exchange_submit_blocked": payload.get("approved_for_exchange_submit") is False and payload.get("exchange_submit_performed") is False,
        "live_real_blocked": payload.get("approved_for_live_real") is False and payload.get("live_real_order_performed") is False,
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
    source_path = root / "src/tradebot/live_real_preflight_gate.py"
    source_text = source_path.read_text(encoding="utf-8", errors="replace") if source_path.exists() else ""
    base_checker = root / "tools/check_4B436630U_paper_promotion_review.py"
    base_report = _run_json_tool(root, "tools/check_4B436630U_paper_promotion_review.py") if base_checker.exists() else {"ok": False, "missing": True}
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30v_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30u_checker_ok": bool(base_report.get("ok")),
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_source_30u_ok": bool(probe.get("source_30u_ok")),
        "module_probe_api_env_capability_audit_ok": bool(probe.get("api_env_capability_audit_ok")),
        "module_probe_account_capability_audit_ok": bool(probe.get("account_capability_audit_ok")),
        "module_probe_hard_submit_block_ok": bool(probe.get("hard_submit_block_ok")),
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
        "base_30u_checker": base_report,
        "module_probe": probe,
        "read_only": True,
        "preflight_only": True,
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
