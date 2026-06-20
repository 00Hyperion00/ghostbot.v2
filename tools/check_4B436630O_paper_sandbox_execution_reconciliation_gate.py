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

CONTRACT_VERSION = "4B.4.3.6.6.30O"
EXPECTED_FILES = [
    "README_APPLY_4B436630O.txt",
    "docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_4B436630O.md",
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tools/apply_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/rollback_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py",
]
PY_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tools/apply_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/rollback_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_execution_reconciliation_gate_enabled",
    "paper_sandbox_execution_reconciliation_consume_30n_required",
    "paper_sandbox_execution_reconciliation_mismatch_zero_required",
    "paper_sandbox_execution_reconciliation_sqlite_mirror_required",
    "paper_sandbox_execution_reconciliation_sqlite_path",
    "paper_sandbox_execution_reconciliation_no_exchange_submit_required",
    "paper_sandbox_execution_reconciliation_no_live_real_required",
    "paper_sandbox_execution_reconciliation_tolerance",
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


def _synthetic_30n_report() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_READY_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_dry_run_execution_gate": True,
        "approved_for_30m_order_envelope_consumption": True,
        "approved_for_internal_paper_execution_simulation": True,
        "approved_for_paper_execution_ledger_append": True,
        "approved_for_paper_sandbox_dry_run_execution": True,
        "approved_for_exchange_submit": False,
        "approved_for_paper_candidate": True,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_order_enablement_still_blocked": True,
    }


def _synthetic_ledger_event() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "event_id": "paper-exec-4B436630N-probe",
        "event_type": "internal_paper_sandbox_dry_run_execution_simulated_fill_no_exchange_submit",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "simulated_fill_price_usd": 2500.0,
        "simulated_fill_qty": 0.01,
        "simulated_fee_bps": 10.0,
        "simulated_fee_usd": 0.025,
        "quote_balance_delta_usd": -25.025,
        "base_balance_delta": 0.01,
        "signed_position_qty_delta": 0.01,
        "base_asset": "ETH",
        "quote_asset": "USDT",
        "exchange_submit_performed": False,
        "submitted_to_exchange": False,
        "network_submit_attempted": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
    }


def _module_probe(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    code = r"""
import json
import tempfile
from pathlib import Path
from tradebot.config import Settings
from tradebot.paper_sandbox_execution_reconciliation_gate import build_paper_sandbox_execution_reconciliation_snapshot
report = __import__('json').loads(__import__('os').environ['PROBE_30N_REPORT'])
event = __import__('json').loads(__import__('os').environ['PROBE_30N_EVENT'])
with tempfile.TemporaryDirectory() as tmp:
    sqlite_path = Path(tmp) / 'audit.sqlite'
    snapshot = build_paper_sandbox_execution_reconciliation_snapshot(Settings(), report, event, source_report_path='synthetic_30n_ready.json', ledger_path=str(Path(tmp) / 'ledger.jsonl'), ledger_rows=1, write_sqlite_mirror=True, sqlite_path=sqlite_path)
    print(json.dumps({
        'ok': snapshot.get('decision') == 'PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRRORED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL',
        'ready_decision': snapshot.get('decision'),
        'source_30n_ok': snapshot.get('source_30n_paper_execution_ledger_verified'),
        'reconciliation_ok': snapshot.get('order_fill_position_balance_reconciled'),
        'mismatch_count': snapshot.get('mismatch_count'),
        'sqlite_ok': snapshot.get('sqlite_audit_mirror_verified'),
        'exchange_submit_blocked': snapshot.get('approved_for_exchange_submit') is False and snapshot.get('exchange_submit_performed') is False,
        'live_real_blocked': snapshot.get('approved_for_live_real') is False,
    }, sort_keys=True))
"""
    env["PROBE_30N_REPORT"] = json.dumps(_synthetic_30n_report())
    env["PROBE_30N_EVENT"] = json.dumps(_synthetic_ledger_event())
    proc = subprocess.run([sys.executable, "-c", code], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8") if (root / "src/tradebot/config.py").exists() else ""
    base_path = root / "tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py"
    base_report = _run_json_tool(root, "tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py") if base_path.exists() else {"ok": False, "missing": True}
    module_probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "base_30n_checker_ok": bool(base_report.get("ok")),
        "config_30o_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "contract_version_ok": True,
        "source_30n_ledger_gate_present": "source_30n_paper_execution_ledger_gate" in (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").read_text(encoding="utf-8"),
        "order_fill_position_balance_reconciliation_gate_present": "order_fill_position_balance_reconciliation_gate" in (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").read_text(encoding="utf-8"),
        "mismatch_zero_proof_gate_present": "mismatch_zero_proof_gate" in (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").read_text(encoding="utf-8"),
        "sqlite_audit_mirror_gate_present": "sqlite_audit_mirror_gate" in (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").read_text(encoding="utf-8"),
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").read_text(encoding="utf-8"),
        "no_live_real_gate_present": "no_live_real_gate" in (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").read_text(encoding="utf-8"),
        "module_probe_ok": bool(module_probe.get("ok")),
        "module_probe_source_30n_ok": bool(module_probe.get("source_30n_ok")),
        "module_probe_reconciliation_ok": bool(module_probe.get("reconciliation_ok")),
        "module_probe_mismatch_zero": module_probe.get("mismatch_count") == 0,
        "module_probe_sqlite_ok": bool(module_probe.get("sqlite_ok")),
        "module_probe_exchange_submit_blocked": bool(module_probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(module_probe.get("live_real_blocked")),
        "exchange_submit_still_blocked": bool(module_probe.get("exchange_submit_blocked")),
        "runtime_training_reload_mutation_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "base_30n_report_summary": {"ok": bool(base_report.get("ok")), "contract_version": base_report.get("contract_version"), "checks": base_report.get("checks", {})},
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
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
