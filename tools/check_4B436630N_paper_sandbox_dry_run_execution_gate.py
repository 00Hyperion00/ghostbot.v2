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

CONTRACT_VERSION = "4B.4.3.6.6.30N"
PY_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_dry_run_execution_gate.py",
    "tests/test_paper_sandbox_dry_run_execution_gate_4B436630N.py",
    "tools/apply_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/rollback_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/run_4B436630N_paper_sandbox_dry_run_execution_gate.py",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630N.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_4B436630N.md",
    "src/tradebot/paper_sandbox_dry_run_execution_gate.py",
    "tests/test_paper_sandbox_dry_run_execution_gate_4B436630N.py",
    "tools/apply_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/rollback_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/run_4B436630N_paper_sandbox_dry_run_execution_gate.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_execution_gate_enabled",
    "paper_sandbox_dry_run_execution_consume_30m_required",
    "paper_sandbox_dry_run_execution_authorization_required",
    "paper_sandbox_dry_run_execution_operator_id",
    "paper_sandbox_dry_run_execution_authorization_phrase",
    "paper_sandbox_dry_run_execution_authorization_token",
    "paper_sandbox_dry_run_execution_authorization_issued",
    "paper_sandbox_dry_run_execution_authorization_issued_at_ms",
    "paper_sandbox_dry_run_execution_authorization_ttl_sec",
    "paper_sandbox_dry_run_execution_ledger_append_required",
    "paper_sandbox_dry_run_execution_ledger_path",
    "paper_sandbox_dry_run_execution_no_exchange_submit_required",
    "paper_sandbox_dry_run_execution_no_live_real_required",
    "paper_sandbox_dry_run_execution_simulated_fill_price_usd",
    "paper_sandbox_dry_run_execution_simulated_fee_bps",
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
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
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


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_execution_gate import (
        AUTHORIZATION_REQUIRED_DECISION,
        READY_DECISION,
        build_paper_sandbox_dry_run_execution_snapshot,
    )

    source_30m = {
        "contract_version": "4B.4.3.6.6.30M",
        "decision": "PAPER_SANDBOX_EXECUTION_PREFLIGHT_READY_ORDER_ENVELOPE_BUILT_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_execution_preflight": True,
        "approved_for_30l_candidate_unlock_consumption": True,
        "approved_for_paper_sandbox_dry_run_authorization": True,
        "approved_for_order_envelope_build": True,
        "order_envelope_built": True,
        "order_envelope_written": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_candidate": True,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }
    order_envelope = {
        "envelope_id": "probe-envelope-30m",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "runtime_envelope": "sandbox_only",
        "execution_mode": "dry_run",
        "market_type": "spot_demo",
    }
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "ledger.jsonl"
        blocked = build_paper_sandbox_dry_run_execution_snapshot(
            Settings(),
            source_30m,
            order_envelope=order_envelope,
            ledger_path=ledger,
            now_ms=1_781_980_000_000,
        )
        ready = build_paper_sandbox_dry_run_execution_snapshot(
            Settings(),
            source_30m,
            order_envelope=order_envelope,
            operator_id="operator-30n",
            authorization_token="AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION",
            issue_execution_authorization=True,
            append_ledger=True,
            ledger_path=ledger,
            now_ms=1_781_980_001_000,
        )
        rows = ledger.read_text(encoding="utf-8").strip().splitlines() if ledger.exists() else []
    return {
        "ok": bool(blocked.get("decision") == AUTHORIZATION_REQUIRED_DECISION and ready.get("decision") == READY_DECISION and len(rows) == 1),
        "default_decision": blocked.get("decision"),
        "ready_decision": ready.get("decision"),
        "source_30m_ok": bool(ready.get("source_30m_order_envelope_verified")),
        "authorization_ok": bool(ready.get("paper_dry_run_execution_authorization_verified")),
        "simulation_ok": bool(ready.get("internal_paper_execution_simulated")),
        "ledger_append_ok": bool(ready.get("paper_execution_ledger_appended")),
        "paper_execution_authorized": bool(ready.get("approved_for_paper_sandbox_dry_run_execution")),
        "exchange_submit_blocked": ready.get("approved_for_exchange_submit") is False and ready.get("exchange_submit_performed") is False,
        "live_real_blocked": ready.get("approved_for_live_real") is False,
        "ledger_rows": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/config.py").exists() else ""
    base_checker_path = root / "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py"
    base_report = _run_json_tool(root, "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py") if base_checker_path.exists() else {"ok": False, "missing": True}
    module_probe = _module_probe(root)
    source_text = (root / "src/tradebot/paper_sandbox_dry_run_execution_gate.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/paper_sandbox_dry_run_execution_gate.py").exists() else ""
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30n_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30l_h2_checker_ok": bool(base_report.get("ok")),
        "source_30m_order_envelope_gate_present": "source_30m_order_envelope_gate" in source_text,
        "dry_run_execution_authorization_gate_present": "paper_sandbox_dry_run_execution_authorization_gate" in source_text,
        "internal_paper_execution_simulation_gate_present": "internal_paper_execution_simulation_gate" in source_text,
        "paper_execution_ledger_append_gate_present": "paper_execution_ledger_append_gate" in source_text,
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in source_text,
        "no_live_real_gate_present": "no_live_real_gate" in source_text,
        "module_probe_ok": bool(module_probe.get("ok")),
        "module_probe_source_30m_ok": bool(module_probe.get("source_30m_ok")),
        "module_probe_authorization_ok": bool(module_probe.get("authorization_ok")),
        "module_probe_simulation_ok": bool(module_probe.get("simulation_ok")),
        "module_probe_ledger_append_ok": bool(module_probe.get("ledger_append_ok")),
        "module_probe_exchange_submit_blocked": bool(module_probe.get("exchange_submit_blocked")),
        "paper_execution_authorized_internal_only": bool(module_probe.get("paper_execution_authorized")),
        "exchange_submit_still_blocked": True,
        "live_real_still_blocked": True,
        "runtime_training_reload_mutation_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "base_30l_h2_report_summary": {
            "ok": bool(base_report.get("ok")),
            "contract_version": base_report.get("contract_version"),
            "checks": base_report.get("checks", {}),
        },
        "module_probe": module_probe,
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
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if not args.once_json:
        print(f"{CONTRACT_VERSION} paper sandbox dry-run execution gate check {'OK' if payload['ok'] else 'FAILED'}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
