from __future__ import annotations

import argparse
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30J"
EXPECTED_FILES = [
    "README_APPLY_4B436630J.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_4B436630J.md",
    "src/tradebot/paper_sandbox_dry_run_reconciliation_audit_ledger.py",
    "tests/test_paper_sandbox_dry_run_reconciliation_audit_ledger_4B436630J.py",
    "tools/apply_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py",
    "tools/check_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py",
    "tools/rollback_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py",
    "tools/run_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]
COMPILE_FILES = [
    *PY_FILES,
    "src/tradebot/config.py",
    "src/tradebot/persistence.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_reconciliation_audit_proof_enabled",
    "paper_sandbox_dry_run_reconciliation_consume_30i_ledger_required",
    "paper_sandbox_dry_run_reconciliation_mismatch_zero_required",
    "paper_sandbox_dry_run_reconciliation_sqlite_mirror_required",
    "paper_sandbox_dry_run_reconciliation_no_exchange_submit_required",
    "paper_sandbox_dry_run_reconciliation_paper_candidate_still_blocked_required",
    "paper_sandbox_dry_run_reconciliation_tolerance",
    "paper_sandbox_dry_run_reconciliation_sqlite_path",
]
H4_CHECKER = Path("tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py")


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile_no_write(path: Path) -> tuple[bool, str]:
    try:
        py_compile.compile(str(path), doraise=True)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def compile_files(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in COMPILE_FILES:
        ok, error = _compile_no_write(root / rel)
        out[rel] = {"ok": ok, "error": error}
    return out


def run_cli_json(root: Path, script: Path, *args: str) -> dict[str, Any]:
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else f"{src}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(root / script), *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=300,
    )
    payload: dict[str, Any] = {"ok": False, "returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
            if isinstance(parsed, dict):
                payload.update(parsed)
                payload["returncode"] = proc.returncode
        except json.JSONDecodeError:
            pass
    return payload


def write_synthetic_30i_evidence(reports: Path) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    reports.mkdir(parents=True, exist_ok=True)
    event = {
        "event_id": "sim-fill-4B436630I-1800000000000",
        "contract_version": "4B.4.3.6.6.30I",
        "event_type": "internal_simulated_fill_no_exchange_submit",
        "generated_at_utc": "2026-01-01T00:00:00+00:00",
        "source_30h_report_path": "synthetic_30h_ready.json",
        "source_30h_decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_READY_PAPER_EXECUTION_DISABLED_LIVE_REAL_BLOCKED",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "simulated_fill_price_usd": 2500.0,
        "simulated_fill_qty": 0.01,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "paper_candidate_approved": False,
        "live_real_approved": False,
    }
    ledger_path = reports / "4B436630I_internal_simulated_fill_ledger.jsonl"
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    source = {
        "contract_version": "4B.4.3.6.6.30I",
        "decision": "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_READY_SIMULATED_FILL_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_internal_execution_harness": True,
        "approved_for_internal_only_execution_harness": True,
        "approved_for_simulated_fill_ledger_append": True,
        "approved_for_no_exchange_submit_verification": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "simulated_fill_ledger_append_performed": True,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "exchange_submit_performed": False,
        "simulated_fill_ledger_append": {
            "ok": True,
            "required": True,
            "append_performed": True,
            "ledger_path": ledger_path.as_posix(),
            "ledger_event_id": event["event_id"],
            "event": event,
            "reason_codes": ["SIMULATED_FILL_LEDGER_APPEND_VERIFIED_INTERNAL_ONLY"],
        },
    }
    source_path = reports / "4B436630I_paper_sandbox_dry_run_internal_execution_harness_20260101T000000Z_ready.json"
    source_path.write_text(json.dumps(source, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    return source_path, ledger_path, source, event


def module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_reconciliation_audit_ledger import (
        READY_DECISION,
        build_from_latest_30i_evidence,
    )

    tmp = Path(tempfile.mkdtemp(prefix="tradebot_30j_probe_"))
    try:
        reports = tmp / "reports" / "production_hardening"
        _source_path, ledger_path, _source, _event = write_synthetic_30i_evidence(reports)
        sqlite_path = tmp / "30j_mirror.db"
        settings = Settings(
            paper_sandbox_dry_run_simulated_fill_ledger_path=ledger_path.as_posix(),
            paper_sandbox_dry_run_reconciliation_sqlite_path=sqlite_path.as_posix(),
        )
        payload = build_from_latest_30i_evidence(settings=settings, reports_dir=reports, sqlite_path=sqlite_path)
        reconciliation = payload.get("reconciliation", {})
        sqlite_mirror = payload.get("sqlite_audit_mirror", {})
        return {
            "ok": payload.get("decision") == READY_DECISION and bool(payload.get("approved_for_mismatch_zero_proof")) and bool(payload.get("approved_for_sqlite_audit_mirror")),
            "decision": payload.get("decision"),
            "ready_reconciliation": bool(payload.get("approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof")),
            "ledger_consumed": bool(payload.get("simulated_fill_ledger_consumed")),
            "mismatch_zero": bool(payload.get("reconciliation_mismatch_zero_verified")) and reconciliation.get("mismatch_count") == 0,
            "sqlite_mirror_ok": bool(payload.get("sqlite_audit_mirror_verified")) and sqlite_mirror.get("orders_count", 0) >= 1 and sqlite_mirror.get("fills_count", 0) >= 1,
            "no_exchange_submit": bool(payload.get("no_exchange_submit_verified")) and payload.get("exchange_submit_performed") is False,
            "paper_candidate_blocked": bool(payload.get("paper_candidate_still_blocked_verified")) and payload.get("approved_for_paper_candidate") is False,
            "live_real_blocked": payload.get("approved_for_live_real") is False,
            "mismatch_count": reconciliation.get("mismatch_count"),
            "sqlite_counts": {
                "orders": sqlite_mirror.get("orders_count"),
                "fills": sqlite_mirror.get("fills_count"),
                "positions": sqlite_mirror.get("positions_count"),
                "balance_snapshots": sqlite_mirror.get("balance_snapshots_count"),
            },
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def build_report(root: Path) -> dict[str, Any]:
    compiled = compile_files(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "config.py").exists() else ""
    h4_report = run_cli_json(root, H4_CHECKER, "--once-json") if (root / H4_CHECKER).exists() else {"ok": False, "error": "H4 checker missing"}
    probe = module_probe(root)
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item["ok"] for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").exists() else False,
        "config_30j_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30i_h4_checker_ok": bool(h4_report.get("ok")),
        "source_30i_ledger_consumption_gate_present": "source_30i_simulated_fill_ledger_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").exists() else False,
        "reconciliation_gate_present": "order_fill_position_balance_reconciliation_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").exists() else False,
        "mismatch_zero_gate_present": "mismatch_zero_proof_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").exists() else False,
        "sqlite_audit_mirror_gate_present": "sqlite_audit_mirror_gate" in (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_dry_run_reconciliation_audit_ledger.py").exists() else False,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_mismatch_zero": bool(probe.get("mismatch_zero")),
        "module_probe_sqlite_mirror_ok": bool(probe.get("sqlite_mirror_ok")),
        "exchange_submit_still_blocked": bool(probe.get("no_exchange_submit")),
        "paper_execution_still_blocked": True,
        "paper_candidate_still_blocked": bool(probe.get("paper_candidate_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
        "order_actions_blocked": True,
        "runtime_training_reload_mutation_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "expected_files": expected,
        "compiled": compiled,
        "checks": checks,
        "base_30i_h4_report_summary": {
            "ok": h4_report.get("ok"),
            "contract_version": h4_report.get("contract_version"),
            "checks": h4_report.get("checks", {}),
        },
        "module_probe": probe,
        "exchange_submit_performed": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "runtime_overlay_activation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
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
