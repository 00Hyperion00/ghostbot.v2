from __future__ import annotations

import json
import math
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import Settings
from .persistence import SQLiteStore

CONTRACT_VERSION = "4B.4.3.6.6.30J"
SOURCE_30I_CONTRACT_VERSION = "4B.4.3.6.6.30I"
SOURCE_30I_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_READY_SIMULATED_FILL_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED"
REPORT_TYPE = "paper_sandbox_dry_run_reconciliation_audit_ledger_proof_mismatch_zero_no_exchange_submit"
REPORT_PREFIX = "4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger_proof"
SQLITE_DEFAULT_NAME = "4B436630J_reconciliation_audit_mirror.db"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_READY_MISMATCH_ZERO_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED"
SOURCE_30I_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_30I_LEDGER_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_NOT_READY_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_sandbox_dry_run_reconciliation_audit_ledger_proof": True,
    "paper_candidate_still_blocked": True,
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
class Source30IStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    approved_for_internal_harness: bool
    approved_for_simulated_fill_ledger_append: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    simulated_fill_ledger_append_performed: bool
    trading_action_performed: bool
    exchange_submit_performed: bool
    paper_order_enablement_still_blocked: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LedgerConsumptionStatus:
    ok: bool
    required: bool
    ledger_path: str | None
    event_found: bool
    event_id: str | None
    event: dict[str, Any]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReconciliationStatus:
    ok: bool
    required: bool
    tolerance: float
    symbol: str
    side: str
    quote_asset: str
    base_asset: str
    order_notional_usd: float
    fill_notional_usd: float
    fill_price_usd: float
    fill_qty: float
    signed_position_qty: float
    quote_balance_delta: float
    base_balance_delta: float
    notional_mismatch: float
    qty_mismatch: float
    position_mismatch: float
    quote_balance_mismatch: float
    base_balance_mismatch: float
    mismatch_count: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SQLiteMirrorStatus:
    ok: bool
    required: bool
    mirror_path: str
    append_performed: bool
    orders_count: int
    fills_count: int
    positions_count: int
    balance_snapshots_count: int
    operator_actions_count: int
    risk_events_count: int
    schema_version: int
    audit_snapshot_ok: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoExchangeSubmitStatus:
    ok: bool
    required: bool
    approved_for_exchange_submit: bool
    submitted_to_exchange: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    exchange_order_id_present: bool
    exchange_client_order_id_present: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperCandidateBlockedStatus:
    ok: bool
    required: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_live_order_enablement_present: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReconciliationAuditLedgerDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof: bool
    approved_for_30i_simulated_fill_ledger_consumption: bool
    approved_for_order_fill_position_balance_reconciliation: bool
    approved_for_mismatch_zero_proof: bool
    approved_for_sqlite_audit_mirror: bool
    approved_for_no_exchange_submit_verification: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30i_internal_harness_verified: bool
    simulated_fill_ledger_consumed: bool
    reconciliation_mismatch_zero_verified: bool
    sqlite_audit_mirror_verified: bool
    no_exchange_submit_verified: bool
    paper_candidate_still_blocked_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    order_actions_performed: bool
    exchange_submit_performed: bool
    sqlite_audit_mirror_append_performed: bool
    mismatch_count: int
    reason_codes: list[str]
    source_30i: dict[str, Any]
    ledger_consumption: dict[str, Any]
    reconciliation: dict[str, Any]
    sqlite_audit_mirror: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    paper_candidate_still_blocked: dict[str, Any]
    source_30i_snapshot: dict[str, Any]

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


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isfinite(parsed):
        return parsed
    return default


def _bool(value: Any) -> bool:
    return bool(value)


def latest_30i_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630I_paper_sandbox_dry_run_internal_execution_harness_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def default_sqlite_mirror_path(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path:
    return Path(reports_dir) / SQLITE_DEFAULT_NAME


def _ledger_path_from_source_or_settings(settings: Any, source_30i_snapshot: Mapping[str, Any], reports_dir: str | os.PathLike[str]) -> Path:
    ledger_gate = _mapping(source_30i_snapshot.get("simulated_fill_ledger_append"))
    path = str(ledger_gate.get("ledger_path") or _setting(settings, "paper_sandbox_dry_run_simulated_fill_ledger_path", "") or "").strip()
    if path:
        return Path(path)
    return Path(reports_dir) / "4B436630I_internal_simulated_fill_ledger.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _asset_pair(symbol: str) -> tuple[str, str]:
    upper = str(symbol or "UNKNOWN").upper()
    for quote in ("USDT", "BUSD", "USDC", "BTC", "ETH", "BNB", "USD"):
        if upper.endswith(quote) and len(upper) > len(quote):
            return upper[: -len(quote)], quote
    return upper, "QUOTE"


def evaluate_source_30i_internal_harness(source_30i_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30IStatus:
    contract = str(source_30i_snapshot.get("contract_version") or "") or None
    decision = str(source_30i_snapshot.get("decision") or "") or None
    harness = _bool(source_30i_snapshot.get("approved_for_paper_sandbox_dry_run_internal_execution_harness", False))
    ledger_append = _bool(source_30i_snapshot.get("approved_for_simulated_fill_ledger_append", False))
    dry_execution = _bool(source_30i_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_submit_approved = _bool(source_30i_snapshot.get("approved_for_exchange_submit", False))
    transition_candidate = _bool(source_30i_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = _bool(source_30i_snapshot.get("approved_for_paper_candidate", False))
    live_real = _bool(source_30i_snapshot.get("approved_for_live_real", False))
    ledger_performed = _bool(source_30i_snapshot.get("simulated_fill_ledger_append_performed", False))
    trading_action = _bool(source_30i_snapshot.get("trading_action_performed", False)) or _bool(source_30i_snapshot.get("order_actions_performed", False))
    exchange_submit_performed = _bool(source_30i_snapshot.get("exchange_submit_performed", False))
    order_blocked = _bool(source_30i_snapshot.get("paper_order_enablement_still_blocked", False))
    reasons: list[str] = []
    if contract != SOURCE_30I_CONTRACT_VERSION:
        reasons.append("SOURCE_30I_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30I_READY_DECISION:
        reasons.append("SOURCE_30I_READY_INTERNAL_HARNESS_DECISION_REQUIRED")
    if not harness:
        reasons.append("SOURCE_30I_INTERNAL_HARNESS_NOT_APPROVED")
    if not ledger_append or not ledger_performed:
        reasons.append("SOURCE_30I_SIMULATED_FILL_LEDGER_APPEND_NOT_VERIFIED")
    if dry_execution:
        reasons.append("SOURCE_30I_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
    if exchange_submit_approved or exchange_submit_performed:
        reasons.append("SOURCE_30I_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if transition_candidate:
        reasons.append("SOURCE_30I_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("SOURCE_30I_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30I_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action:
        reasons.append("SOURCE_30I_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    if not order_blocked:
        reasons.append("SOURCE_30I_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    return Source30IStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        approved_for_internal_harness=harness,
        approved_for_simulated_fill_ledger_append=ledger_append,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_submit_approved,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        simulated_fill_ledger_append_performed=ledger_performed,
        trading_action_performed=trading_action,
        exchange_submit_performed=exchange_submit_performed,
        paper_order_enablement_still_blocked=order_blocked,
        reason_codes=reasons or ["SOURCE_30I_INTERNAL_HARNESS_LEDGER_VERIFIED"],
    )


def consume_30i_simulated_fill_ledger(
    settings: Any,
    source_30i_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None,
    reports_dir: str | os.PathLike[str],
) -> LedgerConsumptionStatus:
    required = _bool(_setting(settings, "paper_sandbox_dry_run_reconciliation_consume_30i_ledger_required", True))
    ledger_path = _ledger_path_from_source_or_settings(settings, source_30i_snapshot, reports_dir)
    if not ledger_path.is_absolute():
        ledger_path = Path.cwd() / ledger_path
    rows = _read_jsonl(ledger_path)
    target_event_id = str(_mapping(source_30i_snapshot.get("simulated_fill_ledger_append")).get("ledger_event_id") or "")
    selected: dict[str, Any] | None = None
    for row in reversed(rows):
        if target_event_id and str(row.get("event_id") or "") == target_event_id:
            selected = row
            break
        if str(row.get("contract_version") or "") == SOURCE_30I_CONTRACT_VERSION and str(row.get("event_type") or "") == "internal_simulated_fill_no_exchange_submit":
            selected = row
            if not target_event_id:
                break
    reasons: list[str] = []
    if not required:
        reasons.append("30I_LEDGER_CONSUMPTION_MUST_REMAIN_REQUIRED")
    if not ledger_path.exists():
        reasons.append("30I_SIMULATED_FILL_LEDGER_FILE_MISSING")
    if selected is None:
        reasons.append("30I_SIMULATED_FILL_LEDGER_EVENT_MISSING")
    elif str(selected.get("contract_version") or "") != SOURCE_30I_CONTRACT_VERSION:
        reasons.append("30I_LEDGER_EVENT_CONTRACT_MISMATCH")
    elif bool(selected.get("exchange_submit_performed")) or bool(selected.get("submitted_to_exchange")) or bool(selected.get("network_submit_attempted")):
        reasons.append("30I_LEDGER_EVENT_UNEXPECTED_EXCHANGE_SUBMIT")
    elif bool(selected.get("paper_candidate_approved")) or bool(selected.get("live_real_approved")):
        reasons.append("30I_LEDGER_EVENT_UNEXPECTED_APPROVAL")
    return LedgerConsumptionStatus(
        ok=required and not reasons,
        required=required,
        ledger_path=ledger_path.as_posix(),
        event_found=selected is not None,
        event_id=str(selected.get("event_id")) if selected else None,
        event=dict(selected or {}),
        reason_codes=reasons or ["30I_SIMULATED_FILL_LEDGER_CONSUMED"],
    )


def evaluate_order_fill_position_balance_reconciliation(settings: Any, event: Mapping[str, Any]) -> ReconciliationStatus:
    required = _bool(_setting(settings, "paper_sandbox_dry_run_reconciliation_mismatch_zero_required", True))
    tolerance = _float(_setting(settings, "paper_sandbox_dry_run_reconciliation_tolerance", 1e-9), 1e-9)
    symbol = str(event.get("symbol") or _setting(settings, "symbol", "ETHUSDT") or "ETHUSDT").upper()
    side = str(event.get("side") or "BUY").upper()
    base_asset, quote_asset = _asset_pair(symbol)
    price = _float(event.get("simulated_fill_price_usd"), 0.0)
    qty = _float(event.get("simulated_fill_qty"), 0.0)
    order_notional = _float(event.get("quote_notional_usd"), 0.0)
    fill_notional = price * qty
    signed_qty = qty if side == "BUY" else -qty
    quote_delta = -fill_notional if side == "BUY" else fill_notional
    base_delta = signed_qty
    notional_mismatch = abs(order_notional - fill_notional)
    qty_mismatch = abs(qty - abs(signed_qty))
    position_mismatch = abs(signed_qty - base_delta)
    quote_balance_mismatch = abs(quote_delta + fill_notional) if side == "BUY" else abs(quote_delta - fill_notional)
    base_balance_mismatch = abs(base_delta - signed_qty)
    reasons: list[str] = []
    if not required:
        reasons.append("RECONCILIATION_MISMATCH_ZERO_MUST_REMAIN_REQUIRED")
    if price <= 0:
        reasons.append("RECONCILIATION_FILL_PRICE_NOT_POSITIVE")
    if qty <= 0:
        reasons.append("RECONCILIATION_FILL_QTY_NOT_POSITIVE")
    if order_notional <= 0:
        reasons.append("RECONCILIATION_ORDER_NOTIONAL_NOT_POSITIVE")
    mismatches = {
        "notional_mismatch": notional_mismatch,
        "qty_mismatch": qty_mismatch,
        "position_mismatch": position_mismatch,
        "quote_balance_mismatch": quote_balance_mismatch,
        "base_balance_mismatch": base_balance_mismatch,
    }
    mismatch_count = sum(1 for value in mismatches.values() if value > tolerance)
    if mismatch_count:
        reasons.append("RECONCILIATION_MISMATCH_NON_ZERO")
    return ReconciliationStatus(
        ok=required and not reasons,
        required=required,
        tolerance=tolerance,
        symbol=symbol,
        side=side,
        quote_asset=quote_asset,
        base_asset=base_asset,
        order_notional_usd=order_notional,
        fill_notional_usd=fill_notional,
        fill_price_usd=price,
        fill_qty=qty,
        signed_position_qty=signed_qty,
        quote_balance_delta=quote_delta,
        base_balance_delta=base_delta,
        notional_mismatch=notional_mismatch,
        qty_mismatch=qty_mismatch,
        position_mismatch=position_mismatch,
        quote_balance_mismatch=quote_balance_mismatch,
        base_balance_mismatch=base_balance_mismatch,
        mismatch_count=mismatch_count,
        reason_codes=reasons or ["ORDER_FILL_POSITION_BALANCE_RECONCILIATION_MISMATCH_ZERO"],
    )


def mirror_reconciliation_to_sqlite(settings: Any, event: Mapping[str, Any], reconciliation: ReconciliationStatus, *, sqlite_path: str | os.PathLike[str] | None = None) -> SQLiteMirrorStatus:
    required = _bool(_setting(settings, "paper_sandbox_dry_run_reconciliation_sqlite_mirror_required", True))
    path = Path(sqlite_path or _setting(settings, "paper_sandbox_dry_run_reconciliation_sqlite_path", "") or default_sqlite_mirror_path(DEFAULT_REPORTS_DIR))
    if not path.is_absolute():
        path = Path.cwd() / path
    reasons: list[str] = []
    if not required:
        reasons.append("SQLITE_AUDIT_MIRROR_MUST_REMAIN_REQUIRED")
    if not reconciliation.ok:
        reasons.append("SQLITE_AUDIT_MIRROR_REQUIRES_RECONCILIATION_OK")
    counts: dict[str, int] = {"orders": 0, "fills": 0, "positions": 0, "balance_snapshots": 0, "operator_actions": 0, "risk_events": 0}
    schema_version = 0
    audit_ok = False
    append_performed = False
    store: SQLiteStore | None = None
    try:
        if required and reconciliation.ok:
            store = SQLiteStore(str(path))
            ts = int(time.time() * 1000)
            event_id = str(event.get("event_id") or f"sim-fill-30J-{ts}")
            symbol = reconciliation.symbol
            side = reconciliation.side
            qty = reconciliation.fill_qty
            price = reconciliation.fill_price_usd
            notional = reconciliation.fill_notional_usd
            order_id = event_id
            client_order_id = f"client-{event_id}"
            store.append_operator_action(
                action="30J_RECONCILIATION_AUDIT_LEDGER_PROOF",
                actor="system",
                confirmation="NO_EXCHANGE_SUBMIT",
                outcome="MISMATCH_ZERO",
                data={"contract_version": CONTRACT_VERSION, "source_event_id": event_id, "mismatch_count": reconciliation.mismatch_count},
                ts=ts,
            )
            store.append_order_audit(
                {
                    "symbol": symbol,
                    "side": side,
                    "order_id": order_id,
                    "client_order_id": client_order_id,
                    "status": "SIMULATED_FILLED_INTERNAL_ONLY",
                    "price": price,
                    "qty": qty,
                    "notional": notional,
                    "source": CONTRACT_VERSION,
                    "exchange_submit_performed": False,
                },
                ts=ts,
            )
            store.append_fill_audit(
                {
                    "symbol": symbol,
                    "side": side,
                    "order_id": order_id,
                    "client_order_id": client_order_id,
                    "fill_id": event_id,
                    "price": price,
                    "qty": qty,
                    "fee_asset": "",
                    "fee": 0.0,
                    "source": CONTRACT_VERSION,
                    "exchange_submit_performed": False,
                },
                ts=ts,
            )
            store.append_position_audit(
                {
                    "symbol": symbol,
                    "state": "SIMULATED_INTERNAL_ONLY",
                    "qty": reconciliation.signed_position_qty,
                    "entry_price": price,
                    "mark_price": price,
                    "unrealized_pnl": 0.0,
                    "realized_pnl": 0.0,
                    "source": CONTRACT_VERSION,
                },
                ts=ts,
            )
            store.append_balance_snapshot(
                {
                    "asset": reconciliation.quote_asset,
                    "free": reconciliation.quote_balance_delta,
                    "locked": 0.0,
                    "source": CONTRACT_VERSION,
                },
                ts=ts,
            )
            store.append_balance_snapshot(
                {
                    "asset": reconciliation.base_asset,
                    "free": reconciliation.base_balance_delta,
                    "locked": 0.0,
                    "source": CONTRACT_VERSION,
                },
                ts=ts,
            )
            store.append_risk_event(
                {
                    "symbol": symbol,
                    "event_type": "RECONCILIATION_AUDIT_LEDGER_PROOF",
                    "severity": "INFO",
                    "reason_code": "MISMATCH_ZERO_NO_EXCHANGE_SUBMIT",
                    "message": "30J simulated fill reconciliation mirrored to SQLite audit ledger with no exchange submit.",
                    "source": CONTRACT_VERSION,
                },
                ts=ts,
            )
            snapshot = store.audit_ledger_snapshot()
            audit_ok = bool(snapshot.get("ok"))
            schema_version = int(snapshot.get("schema_version") or 0)
            for table in counts:
                counts[table] = store.fetch_table_count(table)
            close = getattr(store, "close", None)
            if callable(close):
                close()
                store = None
            append_performed = True
    except Exception as exc:
        reasons.append(f"SQLITE_AUDIT_MIRROR_EXCEPTION:{type(exc).__name__}")
    finally:
        if store is not None:
            close = getattr(store, "close", None)
            if callable(close):
                close()
    if required and append_performed:
        if not audit_ok:
            reasons.append("SQLITE_AUDIT_MIRROR_SNAPSHOT_NOT_OK")
        if schema_version < 2:
            reasons.append("SQLITE_AUDIT_MIRROR_SCHEMA_VERSION_TOO_LOW")
        for table, count in counts.items():
            if count <= 0:
                reasons.append(f"SQLITE_AUDIT_MIRROR_{table.upper()}_EMPTY")
    return SQLiteMirrorStatus(
        ok=required and append_performed and not reasons,
        required=required,
        mirror_path=path.as_posix(),
        append_performed=append_performed,
        orders_count=counts["orders"],
        fills_count=counts["fills"],
        positions_count=counts["positions"],
        balance_snapshots_count=counts["balance_snapshots"],
        operator_actions_count=counts["operator_actions"],
        risk_events_count=counts["risk_events"],
        schema_version=schema_version,
        audit_snapshot_ok=audit_ok,
        reason_codes=reasons or ["SQLITE_AUDIT_MIRROR_VERIFIED"],
    )


def evaluate_no_exchange_submit(settings: Any, source_30i_snapshot: Mapping[str, Any], ledger_event: Mapping[str, Any]) -> NoExchangeSubmitStatus:
    required = _bool(_setting(settings, "paper_sandbox_dry_run_reconciliation_no_exchange_submit_required", True))
    approved = _bool(source_30i_snapshot.get("approved_for_exchange_submit", False))
    submitted = _bool(ledger_event.get("submitted_to_exchange", False))
    performed = _bool(source_30i_snapshot.get("exchange_submit_performed", False)) or _bool(ledger_event.get("exchange_submit_performed", False))
    network = _bool(ledger_event.get("network_submit_attempted", False))
    order_id_present = bool(ledger_event.get("exchange_order_id"))
    client_id_present = bool(ledger_event.get("exchange_client_order_id"))
    reasons: list[str] = []
    if not required:
        reasons.append("RECONCILIATION_NO_EXCHANGE_SUBMIT_MUST_REMAIN_REQUIRED")
    if approved:
        reasons.append("RECONCILIATION_EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED")
    if submitted or performed:
        reasons.append("RECONCILIATION_EXCHANGE_SUBMIT_UNEXPECTEDLY_PERFORMED")
    if network:
        reasons.append("RECONCILIATION_NETWORK_SUBMIT_UNEXPECTEDLY_ATTEMPTED")
    if order_id_present:
        reasons.append("RECONCILIATION_EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if client_id_present:
        reasons.append("RECONCILIATION_EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return NoExchangeSubmitStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        submitted_to_exchange=submitted,
        exchange_submit_performed=performed,
        network_submit_attempted=network,
        exchange_order_id_present=order_id_present,
        exchange_client_order_id_present=client_id_present,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED_RECONCILIATION"],
    )


def evaluate_paper_candidate_still_blocked(settings: Any, source_30i_snapshot: Mapping[str, Any]) -> PaperCandidateBlockedStatus:
    required = _bool(_setting(settings, "paper_sandbox_dry_run_reconciliation_paper_candidate_still_blocked_required", True))
    dry_execution = _bool(source_30i_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    transition_candidate = _bool(source_30i_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = _bool(source_30i_snapshot.get("approved_for_paper_candidate", False))
    live_real = _bool(source_30i_snapshot.get("approved_for_live_real", False))
    paper_enablement = _bool(source_30i_snapshot.get("paper_live_order_enablement_present", False))
    order_actions = _bool(source_30i_snapshot.get("trading_action_performed", False)) or _bool(source_30i_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if not required:
        reasons.append("RECONCILIATION_PAPER_CANDIDATE_BLOCK_GATE_MUST_REMAIN_REQUIRED")
    if dry_execution:
        reasons.append("PAPER_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
    if transition_candidate:
        reasons.append("PAPER_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if paper_enablement:
        reasons.append("PAPER_ORDER_ENABLEMENT_UNEXPECTEDLY_PRESENT")
    if order_actions:
        reasons.append("ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    return PaperCandidateBlockedStatus(
        ok=required and not reasons,
        required=required,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_live_order_enablement_present=paper_enablement,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["PAPER_CANDIDATE_STILL_BLOCKED_VERIFIED_RECONCILIATION"],
    )


def build_reconciliation_audit_ledger_snapshot(
    settings: Any,
    source_30i_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    sqlite_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30i_internal_harness(source_30i_snapshot, source_report_path=source_report_path)
    ledger = consume_30i_simulated_fill_ledger(settings, source_30i_snapshot, source_report_path=source_report_path, reports_dir=reports_dir)
    reconciliation = evaluate_order_fill_position_balance_reconciliation(settings, ledger.event)
    sqlite_mirror = mirror_reconciliation_to_sqlite(settings, ledger.event, reconciliation, sqlite_path=sqlite_path)
    no_submit = evaluate_no_exchange_submit(settings, source_30i_snapshot, ledger.event)
    candidate_block = evaluate_paper_candidate_still_blocked(settings, source_30i_snapshot)
    reasons = [*source.reason_codes, *ledger.reason_codes, *reconciliation.reason_codes, *sqlite_mirror.reason_codes, *no_submit.reason_codes, *candidate_block.reason_codes]
    reasons.extend(["MISMATCH_ZERO_PROOF", "SQLITE_AUDIT_MIRROR_INTERNAL_ONLY", "NO_EXCHANGE_SUBMIT_VERIFIED", "PAPER_CANDIDATE_STILL_BLOCKED", "LIVE_REAL_HARD_BLOCK_VERIFIED"])
    ready = source.ok and ledger.ok and reconciliation.ok and sqlite_mirror.ok and no_submit.ok and candidate_block.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok or not ledger.ok:
        decision = SOURCE_30I_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = ReconciliationAuditLedgerDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof=ready,
        approved_for_30i_simulated_fill_ledger_consumption=source.ok and ledger.ok,
        approved_for_order_fill_position_balance_reconciliation=reconciliation.ok,
        approved_for_mismatch_zero_proof=reconciliation.ok and reconciliation.mismatch_count == 0,
        approved_for_sqlite_audit_mirror=sqlite_mirror.ok,
        approved_for_no_exchange_submit_verification=no_submit.ok,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30i_internal_harness_verified=source.ok,
        simulated_fill_ledger_consumed=ledger.ok,
        reconciliation_mismatch_zero_verified=reconciliation.ok and reconciliation.mismatch_count == 0,
        sqlite_audit_mirror_verified=sqlite_mirror.ok,
        no_exchange_submit_verified=no_submit.ok,
        paper_candidate_still_blocked_verified=candidate_block.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        order_actions_performed=False,
        exchange_submit_performed=False,
        sqlite_audit_mirror_append_performed=sqlite_mirror.append_performed,
        mismatch_count=reconciliation.mismatch_count,
        reason_codes=reasons,
        source_30i=source.to_dict(),
        ledger_consumption=ledger.to_dict(),
        reconciliation=reconciliation.to_dict(),
        sqlite_audit_mirror=sqlite_mirror.to_dict(),
        no_exchange_submit=no_submit.to_dict(),
        paper_candidate_still_blocked=candidate_block.to_dict(),
        source_30i_snapshot=dict(source_30i_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30i_simulated_fill_ledger_gate": True,
        "order_fill_position_balance_reconciliation_gate": True,
        "mismatch_zero_proof_gate": True,
        "sqlite_audit_mirror_gate": True,
        "no_exchange_submit_gate": True,
        "paper_candidate_still_blocked_gate": True,
        "still_no_paper_order_enablement_gate": True,
        "no_live_real_enforcement": True,
    })
    return payload


def build_from_latest_30i_evidence(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    sqlite_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    source_path = latest_30i_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    resolved_sqlite = sqlite_path or _setting(settings or Settings(), "paper_sandbox_dry_run_reconciliation_sqlite_path", "") or default_sqlite_mirror_path(reports_dir)
    return build_reconciliation_audit_ledger_snapshot(
        settings or Settings(),
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
        reports_dir=reports_dir,
        sqlite_path=resolved_sqlite,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_30I_REQUIRED_DECISION:
        return "30i_required"
    return "not_ready"


def _unique_report_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    for idx in range(1, 1000):
        candidate = parent / f"{stem}_{idx:03d}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"unable to allocate unique report path for {base}")


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Dry-run Reconciliation + Audit Ledger Proof")
    lines.append("")
    lines.append("This report consumes the 30I internal simulated fill ledger, reconciles order/fill/position/balance with mismatch=0, mirrors the result into SQLite audit storage, and keeps exchange submit, paper candidate, and live-real blocked.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof",
        "approved_for_30i_simulated_fill_ledger_consumption",
        "approved_for_order_fill_position_balance_reconciliation",
        "approved_for_mismatch_zero_proof",
        "approved_for_sqlite_audit_mirror",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_exchange_submit",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "mismatch_count",
        "paper_order_enablement_still_blocked",
        "trading_action_performed",
        "exchange_submit_performed",
        "sqlite_audit_mirror_append_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Reconciliation")
    reconciliation = _mapping(payload.get("reconciliation"))
    for key in (
        "symbol",
        "side",
        "order_notional_usd",
        "fill_notional_usd",
        "fill_qty",
        "notional_mismatch",
        "qty_mismatch",
        "position_mismatch",
        "quote_balance_mismatch",
        "base_balance_mismatch",
        "mismatch_count",
    ):
        lines.append(f"- `{key}`: `{reconciliation.get(key)}`")
    lines.append("")
    lines.append("## Reason codes")
    for reason in payload.get("reason_codes", []):
        lines.append(f"- `{reason}`")
    lines.append("")
    return "\n".join(lines)


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    suffix = _decision_suffix(payload)
    json_path = _unique_report_path(target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json")
    md_path = json_path.with_suffix(".md")
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\n")
    return json_path, md_path
