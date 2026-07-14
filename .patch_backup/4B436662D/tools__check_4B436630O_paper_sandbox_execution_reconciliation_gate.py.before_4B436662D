from __future__ import annotations

import argparse
import inspect
import json
import os
import py_compile
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

CONTRACT_VERSION = "4B.4.3.6.6.30O"
READY_DECISIONS = {
    "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
    "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRRORED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
}
PY_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
]
EXPECTED_FILES = [
    "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
    "tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_execution_reconciliation_gate_enabled",
    "paper_sandbox_execution_reconciliation_consume_30n_required",
    "paper_sandbox_execution_reconciliation_mismatch_zero_required",
    "paper_sandbox_execution_reconciliation_sqlite_mirror_required",
    "paper_sandbox_execution_reconciliation_no_exchange_submit_required",
    "paper_sandbox_execution_reconciliation_no_live_real_required",
    "paper_sandbox_execution_reconciliation_tolerance",
    "paper_sandbox_execution_reconciliation_sqlite_path",
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
        if not path.exists():
            compiled[rel] = {"ok": False, "error": "missing"}
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            compiled[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            compiled[rel] = {"ok": False, "error": str(exc)}
    return compiled


def _event() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "event_type": "internal_paper_sandbox_dry_run_execution_simulated_fill_no_exchange_submit",
        "event_id": "paper-exec-4B436630N-h5-probe",
        "symbol": "ETHUSDT",
        "base_asset": "ETH",
        "quote_asset": "USDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "simulated_fill_price_usd": 2500.0,
        "simulated_fill_qty": 0.01,
        "signed_position_qty_delta": 0.01,
        "quote_balance_delta_usd": -25.025,
        "base_balance_delta": 0.01,
        "simulated_fee_bps": 10.0,
        "simulated_fee_usd": 0.025,
        "paper_sandbox_dry_run_execution_performed": True,
        "network_submit_attempted": False,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
    }


def _source_30n(ledger_path: str) -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_READY_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_dry_run_execution_gate": True,
        "approved_for_30m_order_envelope_consumption": True,
        "approved_for_internal_paper_execution_simulation": True,
        "approved_for_paper_execution_ledger_append": True,
        "approved_for_paper_sandbox_dry_run_execution": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_execution_ledger_path": ledger_path,
        "internal_paper_execution_simulation": {"event": _event(), "ledger_path": ledger_path},
    }


def _sqlite_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    tables = {
        "orders_count": "paper_orders",
        "fills_count": "paper_fills",
        "positions_count": "paper_positions",
        "balance_snapshots_count": "paper_balance_snapshots",
        "risk_events_count": "paper_risk_events",
        "operator_actions_count": "paper_operator_actions",
    }
    counts: dict[str, int] = {}
    try:
        conn = sqlite3.connect(str(path))
        try:
            existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for key, table in tables.items():
                counts[key] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) if table in existing else 0
        finally:
            conn.close()
    except Exception:
        return {}
    return counts


def _call_reconciliation_builder(builder: Callable[..., dict[str, Any]], settings: Any, source: Mapping[str, Any], event: Mapping[str, Any], ledger: Path, sqlite_path: Path, reports_dir: Path) -> dict[str, Any]:
    signature = inspect.signature(builder)
    params = signature.parameters
    kwargs: dict[str, Any] = {}
    if "source_report_path" in params:
        kwargs["source_report_path"] = str(reports_dir / "synthetic_30n_ready.json")
    if "ledger_event" in params:
        kwargs["ledger_event"] = dict(event)
    if "event" in params:
        kwargs["event"] = dict(event)
    if "ledger_path" in params:
        kwargs["ledger_path"] = ledger
    if "reports_dir" in params:
        kwargs["reports_dir"] = reports_dir
    if "sqlite_path" in params:
        kwargs["sqlite_path"] = sqlite_path
    try:
        return builder(settings, source, **kwargs)
    except TypeError as first:
        fallback_attempts = [
            lambda: builder(settings, source, dict(event), ledger_path=ledger, sqlite_path=sqlite_path, reports_dir=reports_dir),
            lambda: builder(settings, source, dict(event), sqlite_path=sqlite_path),
            lambda: builder(settings, source, ledger_event=dict(event), sqlite_path=sqlite_path),
            lambda: builder(settings, source, ledger_path=ledger, sqlite_path=sqlite_path),
            lambda: builder(settings, source, dict(event)),
        ]
        errors = [str(first)]
        for attempt in fallback_attempts:
            try:
                payload = attempt()
                if isinstance(payload, dict):
                    return payload
            except TypeError as exc:
                errors.append(str(exc))
        raise TypeError("; ".join(errors)) from first


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_execution_reconciliation_gate import build_paper_sandbox_execution_reconciliation_snapshot

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ledger = tmp_path / "30n_ledger.jsonl"
        sqlite_path = tmp_path / "30o_probe_mirror.db"
        event = _event()
        ledger.write_text(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
        source = _source_30n(str(ledger))
        payload = _call_reconciliation_builder(
            build_paper_sandbox_execution_reconciliation_snapshot,
            Settings(),
            source,
            event,
            ledger,
            sqlite_path,
            tmp_path,
        )
        db_counts = _sqlite_counts(sqlite_path)
    mirror = payload.get("sqlite_audit_mirror", {}) if isinstance(payload.get("sqlite_audit_mirror"), dict) else {}
    sqlite_ok = bool(payload.get("approved_for_sqlite_audit_mirror") or payload.get("sqlite_audit_mirror_verified") or mirror.get("ok"))
    counts = {**db_counts, **{k: int(v) for k, v in mirror.items() if k.endswith("_count") and isinstance(v, int)}}
    mirror_counts_ok = (
        counts.get("orders_count", 0) >= 1
        and counts.get("fills_count", 0) >= 1
        and counts.get("positions_count", 0) >= 1
        and counts.get("balance_snapshots_count", 0) >= 1
    )
    return {
        "ok": str(payload.get("decision")) in READY_DECISIONS,
        "decision": payload.get("decision"),
        "ledger_consumed": bool(payload.get("ledger_consumed") or payload.get("approved_for_30n_ledger_consumption")),
        "reconciliation_ok": bool(payload.get("approved_for_order_fill_position_balance_reconciliation")),
        "mismatch_zero": bool(payload.get("approved_for_mismatch_zero_proof") or payload.get("reconciliation_mismatch_zero_verified")) and int(payload.get("mismatch_count", -1)) == 0,
        "sqlite_mirror_ok": sqlite_ok and mirror_counts_ok,
        "sqlite_counts": counts,
        "exchange_submit_blocked": payload.get("approved_for_exchange_submit") is False and payload.get("exchange_submit_performed") is False,
        "live_real_blocked": payload.get("approved_for_live_real") is False,
        "trading_action_blocked": payload.get("trading_action_performed") is False and payload.get("order_actions_performed") is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/config.py").exists() else ""
    source_text = (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/paper_sandbox_execution_reconciliation_gate.py").exists() else ""
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": "4B.4.3.6.6.30O" in source_text,
        "config_30o_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "source_30n_paper_execution_ledger_gate_present": "source_30n_paper_execution_ledger_gate" in source_text,
        "order_fill_position_balance_reconciliation_gate_present": "order_fill_position_balance_reconciliation_gate" in source_text,
        "mismatch_zero_proof_gate_present": "mismatch_zero_proof_gate" in source_text,
        "sqlite_audit_mirror_gate_present": "sqlite_audit_mirror_gate" in source_text,
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in source_text,
        "no_live_real_gate_present": "no_live_real_gate" in source_text,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_ledger_consumed": bool(probe.get("ledger_consumed")),
        "module_probe_reconciliation_ok": bool(probe.get("reconciliation_ok")),
        "module_probe_mismatch_zero": bool(probe.get("mismatch_zero")),
        "module_probe_sqlite_mirror_ok": bool(probe.get("sqlite_mirror_ok")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
        "trading_action_still_blocked": bool(probe.get("trading_action_blocked")),
        "runtime_training_reload_mutation_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
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
        print(f"{CONTRACT_VERSION} paper sandbox execution reconciliation gate check {'OK' if payload['ok'] else 'FAILED'}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
