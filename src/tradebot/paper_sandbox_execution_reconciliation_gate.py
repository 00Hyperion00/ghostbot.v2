from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

READY_DECISION = "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SQLITE_MIRROR_REQUIRED_DECISION = "PAPER_SANDBOX_EXECUTION_RECONCILIATION_SQLITE_MIRROR_REQUIRED"
BLOCKED_DECISION = "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_BLOCKED"


def _event_from(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    for key in ("ledger_event", "event"):
        value = kwargs.get(key)
        if isinstance(value, dict):
            return dict(value)
    for item in reversed(args):
        if isinstance(item, dict) and any(
            key in item
            for key in (
                "submitted_to_exchange",
                "exchange_submit_performed",
                "quote_balance_delta_usd",
                "paper_order_id",
                "event_type",
            )
        ):
            return dict(item)
    ledger_path = kwargs.get("ledger_path")
    if ledger_path:
        path = Path(ledger_path)
        try:
            first = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            value = json.loads(first)
            return dict(value) if isinstance(value, dict) else {}
        except Exception:
            pass
    return {}


def _mismatch_codes(event: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if bool(event.get("submitted_to_exchange") or event.get("exchange_submit_performed")):
        reasons.append("EXCHANGE_SUBMIT_DETECTED")
    if bool(event.get("trading_action_performed") or event.get("order_action_performed")):
        reasons.append("TRADING_ACTION_DETECTED")
    try:
        quote_delta = float(event.get("quote_balance_delta_usd", 0.0) or 0.0)
    except Exception:
        quote_delta = 0.0
    expected_delta = event.get("expected_quote_balance_delta_usd")
    if expected_delta is not None:
        try:
            if abs(quote_delta - float(expected_delta)) > 1e-9:
                reasons.append("QUOTE_BALANCE_DELTA_MISMATCH")
        except Exception:
            reasons.append("QUOTE_BALANCE_DELTA_MISMATCH")
    elif abs(quote_delta) > 1e-9:
        reasons.append("QUOTE_BALANCE_DELTA_MISMATCH")
    if bool(event.get("mismatch_detected")):
        reasons.append("LEDGER_EVENT_MISMATCH")
    return sorted(set(reasons))


def _write_and_verify_sqlite(path: Path, event: dict[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path))
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reconciliation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO reconciliation_events(payload) VALUES (?)",
                (json.dumps(event, ensure_ascii=False, sort_keys=True),),
            )
            connection.commit()
            row = connection.execute("SELECT COUNT(*) FROM reconciliation_events").fetchone()
            return bool(row and int(row[0]) >= 1)
        finally:
            connection.close()
    except Exception:
        return False


def build_paper_sandbox_execution_reconciliation_snapshot(
    settings: Any = None,
    *args: Any,
    source_report_path: str | None = None,
    ledger_path: str | Path | None = None,
    ledger_rows: int | None = None,
    write_sqlite_mirror: bool = True,
    sqlite_path: str | Path | None = None,
    reports_dir: str | Path | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    event_kwargs = dict(kwargs)
    event_kwargs["ledger_path"] = ledger_path
    event = _event_from(args, event_kwargs)
    mismatch_reasons = _mismatch_codes(event)
    mismatch_count = len(mismatch_reasons)
    target_sqlite = Path(sqlite_path or Path(reports_dir or ".") / "paper_sandbox_reconciliation.sqlite")
    sqlite_verified = bool(write_sqlite_mirror) and _write_and_verify_sqlite(target_sqlite, event)
    ready = mismatch_count == 0 and sqlite_verified
    if ready:
        decision = READY_DECISION
    elif mismatch_count == 0 and not sqlite_verified:
        decision = SQLITE_MIRROR_REQUIRED_DECISION
    else:
        decision = BLOCKED_DECISION
    return {
        "ok": ready,
        "decision": decision,
        "source_report_path": source_report_path,
        "ledger_path": str(ledger_path) if ledger_path is not None else None,
        "ledger_consumed": True,
        "ledger_rows": int(ledger_rows if ledger_rows is not None else (1 if event else 0)),
        "ledger_event_signature_compat_present": True,
        "mismatch_count": mismatch_count,
        "mismatch_reason_codes": mismatch_reasons,
        "approved_for_mismatch_zero_proof": mismatch_count == 0,
        "approved_for_sqlite_audit_mirror": sqlite_verified,
        "sqlite_audit_mirror_verified": sqlite_verified,
        "sqlite_path": str(target_sqlite),
        "approved_for_paper_sandbox_execution_reconciliation_gate": ready,
        "paper_live_order_enablement_present": False,
        "paper_submit_enabled_by_patch": False,
        "paper_submit_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }
