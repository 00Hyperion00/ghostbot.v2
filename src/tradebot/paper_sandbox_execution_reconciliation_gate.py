from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30O"
SOURCE_30N_CONTRACT_VERSION = "4B.4.3.6.6.30N"
SOURCE_30N_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_READY_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
REPORT_TYPE = "paper_sandbox_execution_reconciliation_gate_mismatch_zero_sqlite_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630O_paper_sandbox_execution_reconciliation_gate"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
DEFAULT_LEDGER_NAME = "4B436630N_internal_paper_execution_ledger.jsonl"
DEFAULT_SQLITE_NAME = "4B436630O_reconciliation_audit_mirror.sqlite"

READY_DECISION = "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRRORED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOURCE_30N_REQUIRED_DECISION = "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_30N_LEDGER_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SQLITE_MIRROR_REQUIRED_DECISION = "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_SQLITE_MIRROR_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_live_order_blocked": True,
    "paper_order_enablement_still_blocked": True,
    "exchange_submit_blocked": True,
    "live_real_blocked": True,
    "live_real_hard_block_verified": True,
    "runtime_activation_blocked": True,
    "training_reload_blocked": True,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "exchange_submit_performed": False,
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30NLedgerStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    ledger_path: str | None
    ledger_event_present: bool
    ledger_rows: int
    execution_gate: bool
    order_envelope_consumed: bool
    internal_simulation: bool
    ledger_append: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReconciliationStatus:
    ok: bool
    mismatch_count: int
    mismatch_zero: bool
    order_fill_reconciled: bool
    position_reconciled: bool
    balance_reconciled: bool
    expected_quote_notional_usd: float
    actual_quote_notional_usd: float
    expected_fill_qty: float
    actual_fill_qty: float
    expected_fee_usd: float
    actual_fee_usd: float
    expected_quote_balance_delta_usd: float
    actual_quote_balance_delta_usd: float
    expected_base_balance_delta: float
    actual_base_balance_delta: float
    tolerance: float
    mismatch_details: list[str]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SQLiteMirrorStatus:
    ok: bool
    required: bool
    sqlite_mirror_requested: bool
    sqlite_path: str
    orders_rows: int
    fills_rows: int
    positions_rows: int
    balances_rows: int
    audit_summary_rows: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoExchangeSubmitStatus:
    ok: bool
    required: bool
    approved_for_exchange_submit: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    exchange_order_id_present: bool
    exchange_client_order_id_present: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoLiveRealStatus:
    ok: bool
    required: bool
    approved_for_live_real: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSandboxExecutionReconciliationDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_execution_reconciliation_gate: bool
    approved_for_30n_paper_execution_ledger_consumption: bool
    approved_for_order_fill_position_balance_reconciliation: bool
    approved_for_mismatch_zero_proof: bool
    approved_for_sqlite_audit_mirror: bool
    approved_for_no_exchange_submit_verification: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    source_30n_paper_execution_ledger_verified: bool
    order_fill_position_balance_reconciled: bool
    mismatch_count: int
    mismatch_zero_verified: bool
    sqlite_audit_mirror_verified: bool
    no_exchange_submit_verified: bool
    no_live_real_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    order_actions_performed: bool
    exchange_submit_performed: bool
    reason_codes: list[str]
    source_30n: dict[str, Any]
    reconciliation: dict[str, Any]
    sqlite_mirror: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30n_snapshot: dict[str, Any]
    ledger_event: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def write_text_atomic(path: str | os.PathLike[str], text: str) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def latest_30n_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630N_paper_sandbox_dry_run_execution_gate_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def read_jsonl(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    ledger = Path(path)
    if not ledger.exists():
        return []
    rows: list[dict[str, Any]] = []
    with ledger.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def latest_30n_ledger_event(ledger_path: str | os.PathLike[str]) -> tuple[dict[str, Any] | None, int]:
    rows = read_jsonl(ledger_path)
    candidates = [row for row in rows if row.get("contract_version") == SOURCE_30N_CONTRACT_VERSION]
    return (candidates[-1], len(rows)) if candidates else (None, len(rows))


def resolve_ledger_path(
    settings: Any,
    source_30n_snapshot: Mapping[str, Any],
    *,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
) -> Path:
    candidate = str(source_30n_snapshot.get("paper_execution_ledger_path") or "").strip()
    if candidate:
        return Path(candidate)
    configured = str(_setting(settings, "paper_sandbox_dry_run_execution_ledger_path", "") or "").strip()
    if configured:
        return Path(configured)
    return Path(reports_dir) / DEFAULT_LEDGER_NAME


def evaluate_source_30n_ledger(
    source_30n_snapshot: Mapping[str, Any],
    ledger_event: Mapping[str, Any] | None,
    *,
    source_report_path: str | None = None,
    ledger_path: str | None = None,
    ledger_rows: int = 0,
) -> Source30NLedgerStatus:
    event = ledger_event or {}
    contract = str(source_30n_snapshot.get("contract_version") or "") or None
    decision = str(source_30n_snapshot.get("decision") or "") or None
    execution_gate = bool(source_30n_snapshot.get("approved_for_paper_sandbox_dry_run_execution_gate", False))
    envelope = bool(source_30n_snapshot.get("approved_for_30m_order_envelope_consumption", False))
    simulation = bool(source_30n_snapshot.get("approved_for_internal_paper_execution_simulation", False))
    ledger_append = bool(source_30n_snapshot.get("approved_for_paper_execution_ledger_append", False))
    dry_execution = bool(source_30n_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_submit = bool(source_30n_snapshot.get("approved_for_exchange_submit", False))
    live_real = bool(source_30n_snapshot.get("approved_for_live_real", False))
    exchange_performed = bool(source_30n_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30n_snapshot.get("trading_action_performed", False))
    order_actions = bool(source_30n_snapshot.get("order_actions_performed", False))
    event_present = bool(event)
    reasons: list[str] = []
    if contract != SOURCE_30N_CONTRACT_VERSION:
        reasons.append("SOURCE_30N_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30N_READY_DECISION:
        reasons.append("SOURCE_30N_READY_LEDGER_DECISION_REQUIRED")
    if not execution_gate:
        reasons.append("SOURCE_30N_EXECUTION_GATE_NOT_APPROVED")
    if not envelope:
        reasons.append("SOURCE_30N_ORDER_ENVELOPE_CONSUMPTION_NOT_APPROVED")
    if not simulation:
        reasons.append("SOURCE_30N_INTERNAL_SIMULATION_NOT_APPROVED")
    if not ledger_append:
        reasons.append("SOURCE_30N_LEDGER_APPEND_NOT_APPROVED")
    if not dry_execution:
        reasons.append("SOURCE_30N_INTERNAL_DRY_RUN_EXECUTION_FLAG_REQUIRED")
    if exchange_submit or exchange_performed:
        reasons.append("SOURCE_30N_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if live_real:
        reasons.append("SOURCE_30N_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30N_TRADING_OR_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    if not event_present:
        reasons.append("SOURCE_30N_LEDGER_EVENT_MISSING")
    if event_present and event.get("contract_version") != SOURCE_30N_CONTRACT_VERSION:
        reasons.append("SOURCE_30N_LEDGER_EVENT_CONTRACT_MISMATCH")
    if event_present and event.get("event_type") != "internal_paper_sandbox_dry_run_execution_simulated_fill_no_exchange_submit":
        reasons.append("SOURCE_30N_LEDGER_EVENT_TYPE_MISMATCH")
    if event_present and bool(event.get("exchange_submit_performed", False)):
        reasons.append("SOURCE_30N_LEDGER_EVENT_EXCHANGE_SUBMIT_PERFORMED")
    if event_present and bool(event.get("submitted_to_exchange", False)):
        reasons.append("SOURCE_30N_LEDGER_EVENT_SUBMITTED_TO_EXCHANGE")
    if event_present and bool(event.get("network_submit_attempted", False)):
        reasons.append("SOURCE_30N_LEDGER_EVENT_NETWORK_SUBMIT_ATTEMPTED")
    if event_present and bool(event.get("live_real_approved", False)):
        reasons.append("SOURCE_30N_LEDGER_EVENT_LIVE_REAL_APPROVED")
    return Source30NLedgerStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        ledger_path=ledger_path,
        ledger_event_present=event_present,
        ledger_rows=ledger_rows,
        execution_gate=execution_gate,
        order_envelope_consumed=envelope,
        internal_simulation=simulation,
        ledger_append=ledger_append,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_submit,
        approved_for_live_real=live_real,
        exchange_submit_performed=exchange_performed,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30N_PAPER_EXECUTION_LEDGER_VERIFIED"],
    )


def _close_enough(left: float, right: float, tolerance: float) -> bool:
    return abs(left - right) <= max(tolerance, 0.0)


def evaluate_reconciliation(ledger_event: Mapping[str, Any], *, tolerance: float = 1e-9) -> ReconciliationStatus:
    side = str(ledger_event.get("side") or "").upper()
    fill_price = _float(ledger_event.get("simulated_fill_price_usd"), 0.0)
    fill_qty = _float(ledger_event.get("simulated_fill_qty"), 0.0)
    quote_notional = _float(ledger_event.get("quote_notional_usd"), 0.0)
    fee_usd = _float(ledger_event.get("simulated_fee_usd"), 0.0)
    quote_delta = _float(ledger_event.get("quote_balance_delta_usd"), 0.0)
    base_delta = _float(ledger_event.get("base_balance_delta"), ledger_event.get("signed_position_qty_delta", 0.0))
    fee_bps = _float(ledger_event.get("simulated_fee_bps"), 0.0)
    expected_notional = round(fill_price * fill_qty, 12)
    expected_fee = round(expected_notional * fee_bps / 10000.0, 12)
    expected_quote_delta = round(-(expected_notional + expected_fee), 12) if side == "BUY" else round(expected_notional - expected_fee, 12)
    expected_base_delta = round(fill_qty, 12) if side == "BUY" else round(-fill_qty, 12)
    mismatches: list[str] = []
    if not _close_enough(quote_notional, expected_notional, tolerance):
        mismatches.append("ORDER_FILL_NOTIONAL_MISMATCH")
    if not _close_enough(fee_usd, expected_fee, tolerance):
        mismatches.append("FILL_FEE_MISMATCH")
    if not _close_enough(quote_delta, expected_quote_delta, tolerance):
        mismatches.append("QUOTE_BALANCE_DELTA_MISMATCH")
    if not _close_enough(base_delta, expected_base_delta, tolerance):
        mismatches.append("BASE_POSITION_OR_BALANCE_DELTA_MISMATCH")
    if side not in {"BUY", "SELL"}:
        mismatches.append("SIDE_UNSUPPORTED")
    if fill_price <= 0 or fill_qty <= 0 or quote_notional <= 0:
        mismatches.append("NON_POSITIVE_FILL_INPUT")
    mismatch_count = len(mismatches)
    order_fill = not any(item in mismatches for item in ("ORDER_FILL_NOTIONAL_MISMATCH", "FILL_FEE_MISMATCH", "SIDE_UNSUPPORTED", "NON_POSITIVE_FILL_INPUT"))
    position = "BASE_POSITION_OR_BALANCE_DELTA_MISMATCH" not in mismatches and side in {"BUY", "SELL"}
    balance = "QUOTE_BALANCE_DELTA_MISMATCH" not in mismatches and side in {"BUY", "SELL"}
    return ReconciliationStatus(
        ok=mismatch_count == 0,
        mismatch_count=mismatch_count,
        mismatch_zero=mismatch_count == 0,
        order_fill_reconciled=order_fill,
        position_reconciled=position,
        balance_reconciled=balance,
        expected_quote_notional_usd=expected_notional,
        actual_quote_notional_usd=quote_notional,
        expected_fill_qty=fill_qty,
        actual_fill_qty=fill_qty,
        expected_fee_usd=expected_fee,
        actual_fee_usd=fee_usd,
        expected_quote_balance_delta_usd=expected_quote_delta,
        actual_quote_balance_delta_usd=quote_delta,
        expected_base_balance_delta=expected_base_delta,
        actual_base_balance_delta=base_delta,
        tolerance=tolerance,
        mismatch_details=mismatches,
        reason_codes=["ORDER_FILL_POSITION_BALANCE_RECONCILIATION_MISMATCH_ZERO"] if mismatch_count == 0 else mismatches,
    )


def _sqlite_path(settings: Any, reports_dir: str | os.PathLike[str]) -> Path:
    configured = str(_setting(settings, "paper_sandbox_execution_reconciliation_sqlite_path", "") or "").strip()
    if configured:
        return Path(configured)
    return Path(reports_dir) / DEFAULT_SQLITE_NAME


def write_sqlite_audit_mirror(
    path: str | os.PathLike[str],
    *,
    source_report: Mapping[str, Any],
    ledger_event: Mapping[str, Any],
    reconciliation: ReconciliationStatus,
) -> SQLiteMirrorStatus:
    sqlite_path = Path(path)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(sqlite_path))
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS orders (event_id TEXT PRIMARY KEY, symbol TEXT, side TEXT, order_type TEXT, quote_notional_usd REAL, submitted_to_exchange INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS fills (event_id TEXT PRIMARY KEY, fill_price_usd REAL, fill_qty REAL, fee_usd REAL, exchange_submit_performed INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS positions (event_id TEXT PRIMARY KEY, symbol TEXT, base_asset TEXT, position_qty_delta REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS balances (event_id TEXT PRIMARY KEY, quote_asset TEXT, quote_balance_delta_usd REAL, base_balance_delta REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS audit_summary (contract_version TEXT, source_contract_version TEXT, mismatch_count INTEGER, mismatch_zero INTEGER, no_exchange_submit INTEGER, no_live_real INTEGER, generated_at_utc TEXT)")
        event_id = str(ledger_event.get("event_id") or "")
        conn.execute(
            "INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, ledger_event.get("symbol"), ledger_event.get("side"), ledger_event.get("order_type"), _float(ledger_event.get("quote_notional_usd"), 0.0), int(bool(ledger_event.get("submitted_to_exchange", False)))),
        )
        conn.execute(
            "INSERT OR REPLACE INTO fills VALUES (?, ?, ?, ?, ?)",
            (event_id, _float(ledger_event.get("simulated_fill_price_usd"), 0.0), _float(ledger_event.get("simulated_fill_qty"), 0.0), _float(ledger_event.get("simulated_fee_usd"), 0.0), int(bool(ledger_event.get("exchange_submit_performed", False)))),
        )
        conn.execute(
            "INSERT OR REPLACE INTO positions VALUES (?, ?, ?, ?)",
            (event_id, ledger_event.get("symbol"), ledger_event.get("base_asset"), _float(ledger_event.get("signed_position_qty_delta"), _float(ledger_event.get("base_balance_delta"), 0.0))),
        )
        conn.execute(
            "INSERT OR REPLACE INTO balances VALUES (?, ?, ?, ?)",
            (event_id, ledger_event.get("quote_asset"), _float(ledger_event.get("quote_balance_delta_usd"), 0.0), _float(ledger_event.get("base_balance_delta"), 0.0)),
        )
        conn.execute("DELETE FROM audit_summary WHERE contract_version = ?", (CONTRACT_VERSION,))
        conn.execute(
            "INSERT INTO audit_summary VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                CONTRACT_VERSION,
                source_report.get("contract_version"),
                reconciliation.mismatch_count,
                int(reconciliation.mismatch_zero),
                int(not bool(ledger_event.get("exchange_submit_performed", False)) and not bool(ledger_event.get("submitted_to_exchange", False))),
                int(not bool(ledger_event.get("live_real_approved", False))),
                utc_now_iso(),
            ),
        )
        conn.commit()
        rows = {
            "orders_rows": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "fills_rows": conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0],
            "positions_rows": conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0],
            "balances_rows": conn.execute("SELECT COUNT(*) FROM balances").fetchone()[0],
            "audit_summary_rows": conn.execute("SELECT COUNT(*) FROM audit_summary WHERE contract_version = ?", (CONTRACT_VERSION,)).fetchone()[0],
        }
    finally:
        conn.close()
    ok = all(int(value) > 0 for value in rows.values())
    return SQLiteMirrorStatus(
        ok=ok,
        required=True,
        sqlite_mirror_requested=True,
        sqlite_path=str(sqlite_path),
        orders_rows=int(rows["orders_rows"]),
        fills_rows=int(rows["fills_rows"]),
        positions_rows=int(rows["positions_rows"]),
        balances_rows=int(rows["balances_rows"]),
        audit_summary_rows=int(rows["audit_summary_rows"]),
        reason_codes=["SQLITE_AUDIT_MIRROR_WRITTEN"] if ok else ["SQLITE_AUDIT_MIRROR_INCOMPLETE"],
    )


def evaluate_sqlite_mirror(
    settings: Any,
    *,
    sqlite_path: str | os.PathLike[str],
    write_sqlite_mirror_requested: bool,
    source_report: Mapping[str, Any],
    ledger_event: Mapping[str, Any],
    reconciliation: ReconciliationStatus,
) -> SQLiteMirrorStatus:
    required = bool(_setting(settings, "paper_sandbox_execution_reconciliation_sqlite_mirror_required", True))
    if write_sqlite_mirror_requested:
        status = write_sqlite_audit_mirror(sqlite_path, source_report=source_report, ledger_event=ledger_event, reconciliation=reconciliation)
        return SQLiteMirrorStatus(
            ok=status.ok,
            required=required,
            sqlite_mirror_requested=True,
            sqlite_path=status.sqlite_path,
            orders_rows=status.orders_rows,
            fills_rows=status.fills_rows,
            positions_rows=status.positions_rows,
            balances_rows=status.balances_rows,
            audit_summary_rows=status.audit_summary_rows,
            reason_codes=status.reason_codes,
        )
    ok = not required
    return SQLiteMirrorStatus(
        ok=ok,
        required=required,
        sqlite_mirror_requested=False,
        sqlite_path=str(sqlite_path),
        orders_rows=0,
        fills_rows=0,
        positions_rows=0,
        balances_rows=0,
        audit_summary_rows=0,
        reason_codes=["SQLITE_AUDIT_MIRROR_WRITE_REQUIRED"] if required else ["SQLITE_AUDIT_MIRROR_NOT_REQUIRED"],
    )


def evaluate_no_exchange_submit(settings: Any, source_30n_snapshot: Mapping[str, Any], ledger_event: Mapping[str, Any]) -> NoExchangeSubmitStatus:
    required = bool(_setting(settings, "paper_sandbox_execution_reconciliation_no_exchange_submit_required", True))
    approved = bool(source_30n_snapshot.get("approved_for_exchange_submit", False))
    report_performed = bool(source_30n_snapshot.get("exchange_submit_performed", False))
    ledger_performed = bool(ledger_event.get("exchange_submit_performed", False)) or bool(ledger_event.get("submitted_to_exchange", False))
    network = bool(ledger_event.get("network_submit_attempted", False))
    exchange_order_id = bool(ledger_event.get("exchange_order_id"))
    client_order_id = bool(ledger_event.get("exchange_client_order_id"))
    reasons: list[str] = []
    if not required:
        reasons.append("NO_EXCHANGE_SUBMIT_RECONCILIATION_GATE_MUST_REMAIN_REQUIRED")
    if approved or report_performed or ledger_performed:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED_OR_PERFORMED")
    if network:
        reasons.append("NETWORK_SUBMIT_UNEXPECTEDLY_ATTEMPTED")
    if exchange_order_id:
        reasons.append("EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if client_order_id:
        reasons.append("EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return NoExchangeSubmitStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        exchange_submit_performed=report_performed or ledger_performed,
        network_submit_attempted=network,
        exchange_order_id_present=exchange_order_id,
        exchange_client_order_id_present=client_order_id,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED_EXECUTION_RECONCILIATION"],
    )


def evaluate_no_live_real(settings: Any, source_30n_snapshot: Mapping[str, Any], ledger_event: Mapping[str, Any]) -> NoLiveRealStatus:
    required = bool(_setting(settings, "paper_sandbox_execution_reconciliation_no_live_real_required", True))
    approved = bool(source_30n_snapshot.get("approved_for_live_real", False)) or bool(ledger_event.get("live_real_approved", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    reasons: list[str] = []
    if not required:
        reasons.append("NO_LIVE_REAL_RECONCILIATION_GATE_MUST_REMAIN_REQUIRED")
    if approved or live_armed or live_confirm:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_ENABLED_OR_ARMED")
    return NoLiveRealStatus(
        ok=required and not reasons,
        required=required,
        approved_for_live_real=approved,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_confirm,
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_EXECUTION_RECONCILIATION"],
    )


def build_paper_sandbox_execution_reconciliation_snapshot(
    settings: Any,
    source_30n_snapshot: Mapping[str, Any],
    ledger_event: Mapping[str, Any] | None,
    *,
    source_report_path: str | None = None,
    ledger_path: str | None = None,
    ledger_rows: int = 0,
    write_sqlite_mirror: bool = False,
    sqlite_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30n_ledger(
        source_30n_snapshot,
        ledger_event,
        source_report_path=source_report_path,
        ledger_path=ledger_path,
        ledger_rows=ledger_rows,
    )
    event = dict(ledger_event or {})
    tolerance = _float(_setting(settings, "paper_sandbox_execution_reconciliation_tolerance", 1e-9), 1e-9)
    reconciliation = evaluate_reconciliation(event, tolerance=tolerance) if event else ReconciliationStatus(
        ok=False,
        mismatch_count=1,
        mismatch_zero=False,
        order_fill_reconciled=False,
        position_reconciled=False,
        balance_reconciled=False,
        expected_quote_notional_usd=0.0,
        actual_quote_notional_usd=0.0,
        expected_fill_qty=0.0,
        actual_fill_qty=0.0,
        expected_fee_usd=0.0,
        actual_fee_usd=0.0,
        expected_quote_balance_delta_usd=0.0,
        actual_quote_balance_delta_usd=0.0,
        expected_base_balance_delta=0.0,
        actual_base_balance_delta=0.0,
        tolerance=tolerance,
        mismatch_details=["LEDGER_EVENT_MISSING"],
        reason_codes=["LEDGER_EVENT_MISSING"],
    )
    resolved_sqlite_path = Path(sqlite_path) if sqlite_path is not None else _sqlite_path(settings, Path(ledger_path or DEFAULT_REPORTS_DIR).parent if ledger_path else DEFAULT_REPORTS_DIR)
    sqlite_status = evaluate_sqlite_mirror(
        settings,
        sqlite_path=resolved_sqlite_path,
        write_sqlite_mirror_requested=write_sqlite_mirror,
        source_report=source_30n_snapshot,
        ledger_event=event,
        reconciliation=reconciliation,
    )
    no_submit = evaluate_no_exchange_submit(settings, source_30n_snapshot, event)
    no_live = evaluate_no_live_real(settings, source_30n_snapshot, event)
    mismatch_zero_required = bool(_setting(settings, "paper_sandbox_execution_reconciliation_mismatch_zero_required", True))
    mismatch_ok = reconciliation.mismatch_zero if mismatch_zero_required else True
    ready = source.ok and reconciliation.ok and mismatch_ok and sqlite_status.ok and no_submit.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30N_REQUIRED_DECISION
    elif not sqlite_status.ok:
        decision = SQLITE_MIRROR_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    reasons = [*source.reason_codes, *reconciliation.reason_codes, *sqlite_status.reason_codes, *no_submit.reason_codes, *no_live.reason_codes]
    reasons.extend(["ORDER_FILL_POSITION_BALANCE_RECONCILIATION", "MISMATCH_ZERO_PROOF", "NO_EXCHANGE_SUBMIT_VERIFIED", "NO_LIVE_REAL_VERIFIED"])
    payload = PaperSandboxExecutionReconciliationDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_execution_reconciliation_gate=ready,
        approved_for_30n_paper_execution_ledger_consumption=source.ok,
        approved_for_order_fill_position_balance_reconciliation=reconciliation.ok,
        approved_for_mismatch_zero_proof=reconciliation.mismatch_zero,
        approved_for_sqlite_audit_mirror=sqlite_status.ok,
        approved_for_no_exchange_submit_verification=no_submit.ok,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_candidate=True,
        approved_for_live_real=False,
        source_30n_paper_execution_ledger_verified=source.ok,
        order_fill_position_balance_reconciled=reconciliation.ok,
        mismatch_count=reconciliation.mismatch_count,
        mismatch_zero_verified=reconciliation.mismatch_zero,
        sqlite_audit_mirror_verified=sqlite_status.ok,
        no_exchange_submit_verified=no_submit.ok,
        no_live_real_verified=no_live.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        order_actions_performed=False,
        exchange_submit_performed=False,
        reason_codes=reasons,
        source_30n=source.to_dict(),
        reconciliation=reconciliation.to_dict(),
        sqlite_mirror=sqlite_status.to_dict(),
        no_exchange_submit=no_submit.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30n_snapshot=dict(source_30n_snapshot),
        ledger_event=event,
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30n_paper_execution_ledger_gate": True,
        "order_fill_position_balance_reconciliation_gate": True,
        "mismatch_zero_proof_gate": True,
        "sqlite_audit_mirror_gate": True,
        "no_exchange_submit_gate": True,
        "no_live_real_gate": True,
        "sqlite_path": str(resolved_sqlite_path),
        "paper_execution_reconciliation_ready": ready,
    })
    return payload


def build_from_latest_30n_ready_report(
    settings: Any | None = None,
    *,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    write_sqlite_mirror: bool = False,
    sqlite_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path = latest_30n_ready_report(reports_dir)
    if source_path is None:
        return build_paper_sandbox_execution_reconciliation_snapshot(
            resolved_settings,
            {},
            None,
            source_report_path=None,
            ledger_path=str(resolve_ledger_path(resolved_settings, {}, reports_dir=reports_dir)),
            ledger_rows=0,
            write_sqlite_mirror=write_sqlite_mirror,
            sqlite_path=sqlite_path,
        )
    source = load_json(source_path)
    ledger_path = resolve_ledger_path(resolved_settings, source, reports_dir=reports_dir)
    event, ledger_rows = latest_30n_ledger_event(ledger_path)
    return build_paper_sandbox_execution_reconciliation_snapshot(
        resolved_settings,
        source,
        event,
        source_report_path=str(source_path),
        ledger_path=str(ledger_path),
        ledger_rows=ledger_rows,
        write_sqlite_mirror=write_sqlite_mirror,
        sqlite_path=sqlite_path,
    )


def write_markdown_report(path: str | os.PathLike[str], snapshot: Mapping[str, Any]) -> None:
    lines = [
        "# 4B.4.3.6.6.30O Paper Sandbox Execution Reconciliation Gate",
        "",
        "This report consumes the 30N internal paper execution ledger, reconciles order/fill/position/balance, writes a SQLite audit mirror when requested, and keeps exchange submit and live-real blocked.",
        "",
        "## Decision",
        f"- `decision`: `{snapshot.get('decision')}`",
        f"- `read_only`: `{snapshot.get('read_only')}`",
        f"- `approved_for_paper_sandbox_execution_reconciliation_gate`: `{snapshot.get('approved_for_paper_sandbox_execution_reconciliation_gate')}`",
        f"- `approved_for_30n_paper_execution_ledger_consumption`: `{snapshot.get('approved_for_30n_paper_execution_ledger_consumption')}`",
        f"- `approved_for_order_fill_position_balance_reconciliation`: `{snapshot.get('approved_for_order_fill_position_balance_reconciliation')}`",
        f"- `approved_for_mismatch_zero_proof`: `{snapshot.get('approved_for_mismatch_zero_proof')}`",
        f"- `approved_for_sqlite_audit_mirror`: `{snapshot.get('approved_for_sqlite_audit_mirror')}`",
        f"- `approved_for_paper_sandbox_dry_run_execution`: `{snapshot.get('approved_for_paper_sandbox_dry_run_execution')}`",
        f"- `approved_for_exchange_submit`: `{snapshot.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{snapshot.get('approved_for_live_real')}`",
        f"- `mismatch_count`: `{snapshot.get('mismatch_count')}`",
        f"- `exchange_submit_performed`: `{snapshot.get('exchange_submit_performed')}`",
        f"- `trading_action_performed`: `{snapshot.get('trading_action_performed')}`",
        "",
        "## Gate checks",
        f"- `source_30n_paper_execution_ledger_verified`: `{snapshot.get('source_30n_paper_execution_ledger_verified')}`",
        f"- `order_fill_position_balance_reconciled`: `{snapshot.get('order_fill_position_balance_reconciled')}`",
        f"- `mismatch_zero_verified`: `{snapshot.get('mismatch_zero_verified')}`",
        f"- `sqlite_audit_mirror_verified`: `{snapshot.get('sqlite_audit_mirror_verified')}`",
        f"- `no_exchange_submit_verified`: `{snapshot.get('no_exchange_submit_verified')}`",
        f"- `no_live_real_verified`: `{snapshot.get('no_live_real_verified')}`",
        "",
        "## Reason codes",
    ]
    lines.extend(f"- `{item}`" for item in snapshot.get("reason_codes", []))
    write_text_atomic(path, "\n".join(lines) + "\n")


def persist_report(snapshot: Mapping[str, Any], *, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if snapshot.get("decision") == READY_DECISION else "sqlite_required" if snapshot.get("decision") == SQLITE_MIRROR_REQUIRED_DECISION else "not_ready"
    stem = f"{REPORT_PREFIX}_{utc_stamp()}_{suffix}"
    json_path = reports / f"{stem}.json"
    md_path = reports / f"{stem}.md"
    write_json_atomic(json_path, dict(snapshot))
    write_markdown_report(md_path, snapshot)
    return json_path, md_path
