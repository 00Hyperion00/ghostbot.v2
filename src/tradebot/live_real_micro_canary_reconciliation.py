from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30Y-H1"
SOURCE_30X_CONTRACT_VERSION = "4B.4.3.6.6.30X"
SOURCE_30X_READY_DECISION = "FIRST_LIVE_REAL_MICRO_CANARY_GATE_READY_SINGLE_MIN_SIZE_SUBMIT_REQUEST_BUILT_NO_AUTOMATED_NETWORK_SUBMIT"
REPORT_TYPE = "live_real_micro_canary_reconciliation"
REPORT_PREFIX = "4B436630Y_live_real_micro_canary_reconciliation"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
DEFAULT_SUBMIT_REQUEST_FILENAME = "4B436630X_first_live_real_micro_canary_submit_request.json"

READY_DECISION = "LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_EMERGENCY_STOP_ARMED"
EXECUTION_EVIDENCE_REQUIRED_DECISION = "LIVE_REAL_MICRO_CANARY_RECONCILIATION_EXECUTION_EVIDENCE_REQUIRED_NO_PATCH_NETWORK_SUBMIT"
SOURCE_30X_REQUIRED_DECISION = "LIVE_REAL_MICRO_CANARY_RECONCILIATION_30X_SUBMIT_REQUEST_REQUIRED_NO_PATCH_NETWORK_SUBMIT"
MISMATCH_DECISION = "LIVE_REAL_MICRO_CANARY_RECONCILIATION_MISMATCH_DETECTED_EMERGENCY_STOP_REQUIRED"
EMERGENCY_STOP_REQUIRED_DECISION = "LIVE_REAL_MICRO_CANARY_RECONCILIATION_EMERGENCY_STOP_NOT_ARMED_NO_FURTHER_LIVE_REAL"
NOT_READY_DECISION = "LIVE_REAL_MICRO_CANARY_RECONCILIATION_NOT_READY_NO_FURTHER_LIVE_REAL"

RISK_FLAGS: dict[str, bool] = {
    "live_real_micro_canary_reconciliation_only": True,
    "patch_network_submit_disabled": True,
    "patch_exchange_submit_performed": False,
    "patch_network_submit_attempted": False,
    "patch_live_real_order_performed": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30XStatus:
    ok: bool
    source_report_path: str | None
    submit_request_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    submit_request_built: bool
    approved_for_first_live_real_micro_canary_gate: bool
    approved_for_manual_runtime_handoff: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    automated_network_submit_disabled_verified: bool
    source_patch_network_submit_attempted: bool
    source_patch_exchange_submit_performed: bool
    request_symbol: str | None
    request_side: str | None
    request_order_type: str | None
    request_quantity: float
    request_mark_price: float
    request_notional_usd: float
    request_client_order_id: str | None
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExecutionEvidenceStatus:
    ok: bool
    provided: bool
    operator_id: str | None
    execution_source: str | None
    exchange_order_id: str | None
    client_order_id: str | None
    symbol: str | None
    side: str | None
    order_type: str | None
    status: str | None
    filled_quantity: float
    avg_fill_price: float
    fill_notional_usd: float
    fee_amount: float
    fee_asset: str | None
    external_exchange_submit_performed: bool
    external_network_submit_attempted: bool
    external_live_real_order_performed: bool
    patch_network_submit_attempted: bool
    patch_exchange_submit_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReconciliationStatus:
    ok: bool
    mismatch_count: int
    request_execution_match: bool
    account_reconciliation_match: bool
    ledger_reconciliation_match: bool
    symbol_match: bool
    side_match: bool
    quantity_match: bool
    notional_match: bool
    client_order_id_match: bool
    manual_min_notional_quantity_adjustment_requested: bool
    manual_min_notional_quantity_adjustment_accepted: bool
    manual_min_notional_quantity_adjustment_reason: str | None
    max_total_notional_usd: float
    expected_position_delta_qty: float
    account_position_delta_qty: float
    ledger_event_recorded: bool
    ledger_event_id: str | None
    ledger_filled_quantity: float
    ledger_notional_usd: float
    quantity_tolerance: float
    notional_tolerance_usd: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EmergencyStopStatus:
    ok: bool
    required: bool
    emergency_stop_armed: bool
    kill_switch_armed: bool
    no_further_live_real_submit_approved: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LiveRealMicroCanaryReconciliationSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_live_real_micro_canary_reconciliation: bool
    approved_for_post_canary_review: bool
    approved_for_additional_exchange_submit: bool
    approved_for_live_real_continuation: bool
    source_30x_submit_request_verified: bool
    execution_evidence_verified: bool
    fill_reconciliation_verified: bool
    account_reconciliation_verified: bool
    ledger_reconciliation_verified: bool
    mismatch_zero_verified: bool
    emergency_stop_armed_verified: bool
    mismatch_count: int
    external_exchange_submit_performed: bool
    external_network_submit_attempted: bool
    external_live_real_order_performed: bool
    patch_exchange_submit_performed: bool
    patch_network_submit_attempted: bool
    patch_live_real_order_performed: bool
    further_live_real_submit_blocked: bool
    reason_codes: list[str]
    source_30x: dict[str, Any]
    execution_evidence: dict[str, Any]
    reconciliation: dict[str, Any]
    emergency_stop: dict[str, Any]
    source_30x_snapshot: dict[str, Any]
    submit_request_snapshot: dict[str, Any]
    execution_evidence_snapshot: dict[str, Any]

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
        tmp = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp.replace(resolved)
    finally:
        tmp.unlink(missing_ok=True)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default if value is None else bool(value)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def _first_present(mapping: Mapping[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


def _nested(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in ("checks", "module_probe", "source_30x", "order_request", "hard_caps", "micro_canary_approval", "no_automated_network_submit"):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def evaluate_source_30x_submit_request(
    source_30x_snapshot: Mapping[str, Any],
    submit_request_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    submit_request_path: str | None = None,
) -> Source30XStatus:
    nested = _nested(source_30x_snapshot)
    contract = str(source_30x_snapshot.get("contract_version") or "") or None
    decision = str(source_30x_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30X_READY_DECISION
    submit_request_built = _boolish(_first_present(source_30x_snapshot, ("submit_request_built",), nested.get("submit_request_built", False)), False)
    gate = _boolish(source_30x_snapshot.get("approved_for_first_live_real_micro_canary_gate", decision_ok), decision_ok)
    handoff = _boolish(source_30x_snapshot.get("approved_for_manual_runtime_handoff", decision_ok), decision_ok)
    approved_exchange = _boolish(source_30x_snapshot.get("approved_for_exchange_submit", False), False)
    approved_live = _boolish(source_30x_snapshot.get("approved_for_live_real", False), False)
    auto_disabled = _boolish(source_30x_snapshot.get("automated_network_submit_disabled_verified", nested.get("automated_network_submit_disabled", True)), True)
    source_network = _boolish(source_30x_snapshot.get("network_submit_attempted", False), False)
    source_exchange = _boolish(source_30x_snapshot.get("exchange_submit_performed", False), False)
    req_symbol = str(submit_request_snapshot.get("symbol") or source_30x_snapshot.get("symbol") or nested.get("symbol") or "").upper() or None
    req_side = str(submit_request_snapshot.get("side") or nested.get("side") or "").upper() or None
    req_type = str(submit_request_snapshot.get("order_type") or nested.get("order_type") or "").upper() or None
    req_qty = _float(submit_request_snapshot.get("quantity", nested.get("quantity", 0.0)), 0.0)
    req_price = _float(submit_request_snapshot.get("mark_price_reference", submit_request_snapshot.get("mark_price", nested.get("mark_price", 0.0))), 0.0)
    req_notional = _float(submit_request_snapshot.get("notional_usd_reference", submit_request_snapshot.get("notional_usd", nested.get("notional_usd", req_qty * req_price))), req_qty * req_price)
    req_client = str(submit_request_snapshot.get("client_order_id") or nested.get("client_order_id") or "") or None
    req_contract = str(submit_request_snapshot.get("contract_version") or "") or None
    request_ok = (
        req_contract in {SOURCE_30X_CONTRACT_VERSION, None}
        and bool(req_symbol)
        and req_side in {"BUY", "SELL"}
        and req_type in {"MARKET", "LIMIT"}
        and req_qty > 0
        and req_notional > 0
        and bool(req_client)
    )
    ok = (
        contract == SOURCE_30X_CONTRACT_VERSION
        and decision_ok
        and submit_request_built
        and gate
        and handoff
        and approved_exchange
        and approved_live
        and auto_disabled
        and not source_network
        and not source_exchange
        and request_ok
    )
    reasons: list[str] = []
    if contract != SOURCE_30X_CONTRACT_VERSION:
        reasons.append("SOURCE_30X_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30X_READY_DECISION_REQUIRED")
    if not submit_request_built or not request_ok:
        reasons.append("SOURCE_30X_SUBMIT_REQUEST_REQUIRED")
    if not gate or not handoff or not approved_exchange or not approved_live:
        reasons.append("SOURCE_30X_APPROVAL_CHAIN_NOT_READY")
    if not auto_disabled or source_network or source_exchange:
        reasons.append("SOURCE_30X_PATCH_NETWORK_SUBMIT_MUST_BE_ZERO")
    return Source30XStatus(
        ok=ok,
        source_report_path=source_report_path,
        submit_request_path=submit_request_path,
        source_contract_version=contract,
        source_decision=decision,
        submit_request_built=submit_request_built,
        approved_for_first_live_real_micro_canary_gate=gate,
        approved_for_manual_runtime_handoff=handoff,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        automated_network_submit_disabled_verified=auto_disabled,
        source_patch_network_submit_attempted=source_network,
        source_patch_exchange_submit_performed=source_exchange,
        request_symbol=req_symbol,
        request_side=req_side,
        request_order_type=req_type,
        request_quantity=req_qty,
        request_mark_price=req_price,
        request_notional_usd=req_notional,
        request_client_order_id=req_client,
        reason_codes=reasons or ["SOURCE_30X_SUBMIT_REQUEST_VERIFIED"],
    )


def evaluate_execution_evidence(evidence: Mapping[str, Any]) -> ExecutionEvidenceStatus:
    provided = bool(evidence)
    symbol = str(evidence.get("symbol") or "").upper() or None
    side = str(evidence.get("side") or "").upper() or None
    order_type = str(evidence.get("order_type") or "MARKET").upper() or None
    status = str(evidence.get("status") or "").upper() or None
    qty = _float(evidence.get("filled_quantity", evidence.get("executed_quantity", evidence.get("quantity", 0.0))), 0.0)
    price = _float(evidence.get("avg_fill_price", evidence.get("average_price", evidence.get("mark_price", 0.0))), 0.0)
    notional = _float(evidence.get("fill_notional_usd", evidence.get("notional_usd", qty * price)), qty * price)
    exchange_submit = _boolish(evidence.get("external_exchange_submit_performed", evidence.get("exchange_submit_performed", provided)), provided)
    network_submit = _boolish(evidence.get("external_network_submit_attempted", evidence.get("network_submit_attempted", provided)), provided)
    live_order = _boolish(evidence.get("external_live_real_order_performed", evidence.get("live_real_order_performed", provided)), provided)
    patch_network = _boolish(evidence.get("patch_network_submit_attempted", False), False)
    patch_exchange = _boolish(evidence.get("patch_exchange_submit_performed", False), False)
    exchange_order_id = str(evidence.get("exchange_order_id") or evidence.get("order_id") or "") or None
    client_order_id = str(evidence.get("client_order_id") or "") or None
    ok = (
        provided
        and bool(symbol)
        and side in {"BUY", "SELL"}
        and order_type in {"MARKET", "LIMIT"}
        and status in {"FILLED"}
        and qty > 0
        and price > 0
        and notional > 0
        and bool(exchange_order_id)
        and exchange_submit
        and network_submit
        and live_order
        and not patch_network
        and not patch_exchange
    )
    reasons: list[str] = []
    if not provided:
        reasons.append("EXECUTION_EVIDENCE_REQUIRED")
    if provided and not bool(exchange_order_id):
        reasons.append("EXCHANGE_ORDER_ID_REQUIRED")
    if provided and status != "FILLED":
        reasons.append("EXECUTION_STATUS_FILLED_REQUIRED")
    if provided and (qty <= 0 or price <= 0 or notional <= 0):
        reasons.append("EXECUTION_FILL_QUANTITY_PRICE_NOTIONAL_REQUIRED")
    if provided and not (exchange_submit and network_submit and live_order):
        reasons.append("EXTERNAL_LIVE_REAL_EXECUTION_FLAGS_REQUIRED")
    if patch_network or patch_exchange:
        reasons.append("PATCH_MUST_NOT_PERFORM_NETWORK_SUBMIT")
    return ExecutionEvidenceStatus(
        ok=ok,
        provided=provided,
        operator_id=str(evidence.get("operator_id") or "") or None,
        execution_source=str(evidence.get("execution_source") or "manual_operator_runtime") if provided else None,
        exchange_order_id=exchange_order_id,
        client_order_id=client_order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        status=status,
        filled_quantity=qty,
        avg_fill_price=price,
        fill_notional_usd=notional,
        fee_amount=_float(evidence.get("fee_amount", evidence.get("commission", 0.0)), 0.0),
        fee_asset=str(evidence.get("fee_asset") or evidence.get("commission_asset") or "") or None,
        external_exchange_submit_performed=exchange_submit,
        external_network_submit_attempted=network_submit,
        external_live_real_order_performed=live_order,
        patch_network_submit_attempted=patch_network,
        patch_exchange_submit_performed=patch_exchange,
        reason_codes=reasons or ["EXTERNAL_EXECUTION_EVIDENCE_VERIFIED"],
    )


def evaluate_reconciliation(settings: Any, source: Source30XStatus, execution: ExecutionEvidenceStatus, evidence: Mapping[str, Any]) -> ReconciliationStatus:
    qty_tol = _float(_setting(settings, "live_real_micro_canary_reconciliation_quantity_tolerance", 1e-9), 1e-9)
    notional_tol = _float(_setting(settings, "live_real_micro_canary_reconciliation_notional_tolerance_usd", 0.50), 0.50)
    min_notional = _float(_setting(settings, "live_real_micro_canary_min_notional_usd", 5.0), 5.0)
    max_total_notional = _float(_setting(settings, "live_real_micro_canary_max_total_notional_usd", 10.0), 10.0)
    adjustment_allowed_by_config = _boolish(_setting(settings, "live_real_micro_canary_reconciliation_allow_min_notional_quantity_adjustment", True), True)
    adjustment_requested = _boolish(evidence.get("manual_min_notional_quantity_adjustment", evidence.get("allow_min_notional_quantity_adjustment", False)), False)
    adjustment_reason = str(evidence.get("quantity_adjustment_reason") or evidence.get("manual_min_notional_quantity_adjustment_reason") or "").strip() or None
    reason_required = _boolish(_setting(settings, "live_real_micro_canary_reconciliation_min_notional_adjustment_requires_operator_reason", True), True)
    expected_delta = execution.filled_quantity if source.request_side == "BUY" else -execution.filled_quantity
    account_delta = _float(evidence.get("account_position_delta_qty", expected_delta if execution.ok else 0.0), 0.0)
    ledger_recorded = _boolish(evidence.get("ledger_event_recorded", bool(evidence.get("ledger_event_id"))), False)
    ledger_id = str(evidence.get("ledger_event_id") or "") or None
    ledger_qty = _float(evidence.get("ledger_filled_quantity", execution.filled_quantity if ledger_recorded else 0.0), 0.0)
    ledger_notional = _float(evidence.get("ledger_notional_usd", execution.fill_notional_usd if ledger_recorded else 0.0), 0.0)
    symbol_match = source.request_symbol == execution.symbol
    side_match = source.request_side == execution.side
    raw_quantity_match = abs(source.request_quantity - execution.filled_quantity) <= qty_tol
    notional_match = abs(source.request_notional_usd - execution.fill_notional_usd) <= notional_tol
    adjustment_reason_ok = (not reason_required) or bool(adjustment_reason)
    manual_adjustment_accepted = (
        not raw_quantity_match
        and adjustment_requested
        and adjustment_allowed_by_config
        and adjustment_reason_ok
        and symbol_match
        and side_match
        and notional_match
        and execution.filled_quantity > 0
        and source.request_quantity > 0
        and execution.fill_notional_usd > 0
        and execution.fill_notional_usd <= max_total_notional
        and execution.fill_notional_usd >= max(0.0, min_notional - notional_tol)
    )
    qty_match = raw_quantity_match or manual_adjustment_accepted
    client_match = not source.request_client_order_id or not execution.client_order_id or source.request_client_order_id == execution.client_order_id
    req_exec = execution.ok and symbol_match and side_match and qty_match and notional_match and client_match
    account_match = abs(account_delta - expected_delta) <= qty_tol
    ledger_match = ledger_recorded and bool(ledger_id) and abs(ledger_qty - execution.filled_quantity) <= qty_tol and abs(ledger_notional - execution.fill_notional_usd) <= notional_tol
    mismatches: list[str] = []
    if not symbol_match:
        mismatches.append("SYMBOL_MISMATCH")
    if not side_match:
        mismatches.append("SIDE_MISMATCH")
    if not qty_match:
        mismatches.append("QUANTITY_MISMATCH")
    elif manual_adjustment_accepted:
        mismatches.append("MANUAL_MIN_NOTIONAL_QUANTITY_ADJUSTMENT_ACCEPTED")
    if not notional_match:
        mismatches.append("NOTIONAL_MISMATCH")
    if not client_match:
        mismatches.append("CLIENT_ORDER_ID_MISMATCH")
    if adjustment_requested and not adjustment_reason_ok:
        mismatches.append("QUANTITY_ADJUSTMENT_REASON_REQUIRED")
    if adjustment_requested and not adjustment_allowed_by_config:
        mismatches.append("QUANTITY_ADJUSTMENT_DISABLED_BY_CONFIG")
    if not account_match:
        mismatches.append("ACCOUNT_POSITION_DELTA_MISMATCH")
    if not ledger_match:
        mismatches.append("LEDGER_RECONCILIATION_MISMATCH")
    blocking_mismatches = [item for item in mismatches if item != "MANUAL_MIN_NOTIONAL_QUANTITY_ADJUSTMENT_ACCEPTED"]
    mismatch_count = len(blocking_mismatches)
    ok = source.ok and execution.ok and req_exec and account_match and ledger_match and mismatch_count == 0
    return ReconciliationStatus(
        ok=ok,
        mismatch_count=mismatch_count,
        request_execution_match=req_exec,
        account_reconciliation_match=account_match,
        ledger_reconciliation_match=ledger_match,
        symbol_match=symbol_match,
        side_match=side_match,
        quantity_match=qty_match,
        notional_match=notional_match,
        client_order_id_match=client_match,
        manual_min_notional_quantity_adjustment_requested=adjustment_requested,
        manual_min_notional_quantity_adjustment_accepted=manual_adjustment_accepted,
        manual_min_notional_quantity_adjustment_reason=adjustment_reason,
        max_total_notional_usd=max_total_notional,
        expected_position_delta_qty=expected_delta,
        account_position_delta_qty=account_delta,
        ledger_event_recorded=ledger_recorded,
        ledger_event_id=ledger_id,
        ledger_filled_quantity=ledger_qty,
        ledger_notional_usd=ledger_notional,
        quantity_tolerance=qty_tol,
        notional_tolerance_usd=notional_tol,
        reason_codes=mismatches or ["LIVE_REAL_MICRO_CANARY_RECONCILIATION_MISMATCH_ZERO"],
    )


def evaluate_emergency_stop(settings: Any, evidence: Mapping[str, Any]) -> EmergencyStopStatus:
    required = _boolish(_setting(settings, "live_real_micro_canary_reconciliation_emergency_stop_required", True), True)
    armed = _boolish(evidence.get("emergency_stop_armed", _setting(settings, "live_real_micro_canary_reconciliation_emergency_stop_armed", True)), True)
    kill = _boolish(evidence.get("kill_switch_armed", _setting(settings, "live_real_micro_canary_reconciliation_kill_switch_armed", True)), True)
    no_further = not _boolish(evidence.get("approved_for_additional_exchange_submit", False), False)
    ok = ((not required) or (armed and kill)) and no_further
    reasons: list[str] = []
    if required and not armed:
        reasons.append("EMERGENCY_STOP_NOT_ARMED")
    if required and not kill:
        reasons.append("KILL_SWITCH_NOT_ARMED")
    if not no_further:
        reasons.append("FURTHER_LIVE_REAL_SUBMIT_MUST_REMAIN_BLOCKED")
    return EmergencyStopStatus(
        ok=ok,
        required=required,
        emergency_stop_armed=armed,
        kill_switch_armed=kill,
        no_further_live_real_submit_approved=no_further,
        reason_codes=reasons or ["EMERGENCY_STOP_AND_KILL_SWITCH_ARMED"],
    )


def build_manual_execution_evidence(
    source: Source30XStatus,
    *,
    operator_id: str | None,
    exchange_order_id: str | None,
    client_order_id: str | None = None,
    filled_quantity: float | str | None = None,
    avg_fill_price: float | str | None = None,
    account_position_delta_qty: float | str | None = None,
    ledger_event_id: str | None = None,
    ledger_filled_quantity: float | str | None = None,
    ledger_notional_usd: float | str | None = None,
    emergency_stop_armed: bool = True,
    allow_min_notional_quantity_adjustment: bool = False,
    quantity_adjustment_reason: str | None = None,
) -> dict[str, Any]:
    qty = _float(filled_quantity if filled_quantity is not None else source.request_quantity, source.request_quantity)
    price = _float(avg_fill_price if avg_fill_price is not None else source.request_mark_price, source.request_mark_price)
    notional = qty * price
    expected_delta = qty if source.request_side == "BUY" else -qty
    return {
        "contract_version": CONTRACT_VERSION,
        "evidence_type": "manual_operator_runtime_exchange_execution_evidence",
        "created_at_utc": utc_now_iso(),
        "operator_id": operator_id,
        "execution_source": "manual_operator_runtime",
        "exchange_order_id": exchange_order_id,
        "client_order_id": client_order_id or source.request_client_order_id,
        "symbol": source.request_symbol,
        "side": source.request_side,
        "order_type": source.request_order_type or "MARKET",
        "status": "FILLED",
        "filled_quantity": qty,
        "avg_fill_price": price,
        "fill_notional_usd": notional,
        "external_exchange_submit_performed": True,
        "external_network_submit_attempted": True,
        "external_live_real_order_performed": True,
        "patch_exchange_submit_performed": False,
        "patch_network_submit_attempted": False,
        "account_position_delta_qty": _float(account_position_delta_qty if account_position_delta_qty is not None else expected_delta, expected_delta),
        "ledger_event_recorded": True,
        "ledger_event_id": ledger_event_id or f"ledger-30y-{utc_stamp()}",
        "ledger_filled_quantity": _float(ledger_filled_quantity if ledger_filled_quantity is not None else qty, qty),
        "ledger_notional_usd": _float(ledger_notional_usd if ledger_notional_usd is not None else notional, notional),
        "emergency_stop_armed": emergency_stop_armed,
        "kill_switch_armed": emergency_stop_armed,
        "approved_for_additional_exchange_submit": False,
        "manual_min_notional_quantity_adjustment": bool(allow_min_notional_quantity_adjustment),
        "quantity_adjustment_reason": quantity_adjustment_reason,
    }


def build_live_real_micro_canary_reconciliation_snapshot(
    settings: Any | None = None,
    source_30x_snapshot: Mapping[str, Any] | None = None,
    submit_request_snapshot: Mapping[str, Any] | None = None,
    execution_evidence_snapshot: Mapping[str, Any] | None = None,
    *,
    source_report_path: str | None = None,
    submit_request_path: str | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_snapshot = dict(_mapping(source_30x_snapshot))
    request_snapshot = dict(_mapping(submit_request_snapshot))
    evidence_snapshot = dict(_mapping(execution_evidence_snapshot))
    source = evaluate_source_30x_submit_request(source_snapshot, request_snapshot, source_report_path=source_report_path, submit_request_path=submit_request_path)
    execution = evaluate_execution_evidence(evidence_snapshot)
    reconciliation = evaluate_reconciliation(resolved_settings, source, execution, evidence_snapshot)
    emergency = evaluate_emergency_stop(resolved_settings, evidence_snapshot)
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not execution.ok:
        reasons.extend(execution.reason_codes)
    if not reconciliation.ok:
        reasons.extend(reconciliation.reason_codes)
    if not emergency.ok:
        reasons.extend(emergency.reason_codes)
    if source.ok and not execution.provided:
        decision = EXECUTION_EVIDENCE_REQUIRED_DECISION
    elif not source.ok:
        decision = SOURCE_30X_REQUIRED_DECISION
    elif not emergency.ok:
        decision = EMERGENCY_STOP_REQUIRED_DECISION
    elif not reconciliation.ok:
        decision = MISMATCH_DECISION
    elif source.ok and execution.ok and reconciliation.ok and emergency.ok:
        decision = READY_DECISION
    else:
        decision = NOT_READY_DECISION
    ready = decision == READY_DECISION
    snapshot = LiveRealMicroCanaryReconciliationSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_30X_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_live_real_micro_canary_reconciliation=ready,
        approved_for_post_canary_review=ready,
        approved_for_additional_exchange_submit=False,
        approved_for_live_real_continuation=False,
        source_30x_submit_request_verified=source.ok,
        execution_evidence_verified=execution.ok,
        fill_reconciliation_verified=reconciliation.request_execution_match,
        account_reconciliation_verified=reconciliation.account_reconciliation_match,
        ledger_reconciliation_verified=reconciliation.ledger_reconciliation_match,
        mismatch_zero_verified=reconciliation.mismatch_count == 0 and reconciliation.ok,
        emergency_stop_armed_verified=emergency.ok,
        mismatch_count=reconciliation.mismatch_count,
        external_exchange_submit_performed=execution.external_exchange_submit_performed if execution.provided else False,
        external_network_submit_attempted=execution.external_network_submit_attempted if execution.provided else False,
        external_live_real_order_performed=execution.external_live_real_order_performed if execution.provided else False,
        patch_exchange_submit_performed=False,
        patch_network_submit_attempted=False,
        patch_live_real_order_performed=False,
        further_live_real_submit_blocked=True,
        reason_codes=reasons or ["LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY"],
        source_30x=source.to_dict(),
        execution_evidence=execution.to_dict(),
        reconciliation=reconciliation.to_dict(),
        emergency_stop=emergency.to_dict(),
        source_30x_snapshot=source_snapshot,
        submit_request_snapshot=request_snapshot,
        execution_evidence_snapshot=evidence_snapshot,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    return snapshot


def latest_valid_30x_report_and_request(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any], Path | None, dict[str, Any]]:
    root = Path(reports_dir)
    candidates = sorted(
        root.glob("4B436630X_first_live_real_micro_canary_*_ready.json"),
        key=lambda item: item.stat().st_mtime if item.exists() else 0.0,
        reverse=True,
    )
    for path in candidates:
        try:
            source = load_json(path)
        except Exception:
            continue
        if not isinstance(source, Mapping):
            continue
        request_path_raw = source.get("submit_request_path") or DEFAULT_SUBMIT_REQUEST_FILENAME
        request_path = Path(str(request_path_raw))
        if not request_path.is_absolute():
            request_path = root / request_path.name
        if not request_path.exists():
            request_path = root / DEFAULT_SUBMIT_REQUEST_FILENAME
        try:
            request = load_json(request_path)
        except Exception:
            request = {}
        if isinstance(request, Mapping):
            status = evaluate_source_30x_submit_request(source, request, source_report_path=str(path), submit_request_path=str(request_path))
            if status.ok:
                return path, dict(source), request_path, dict(request)
    return None, {}, None, {}


def build_from_latest_30x_report_and_request(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    execution_evidence_json: str | os.PathLike[str] | None = None,
    operator_executed: bool = False,
    operator_id: str | None = None,
    exchange_order_id: str | None = None,
    client_order_id: str | None = None,
    filled_quantity: float | str | None = None,
    avg_fill_price: float | str | None = None,
    account_position_delta_qty: float | str | None = None,
    ledger_event_id: str | None = None,
    ledger_filled_quantity: float | str | None = None,
    ledger_notional_usd: float | str | None = None,
    emergency_stop_armed: bool = True,
    allow_min_notional_quantity_adjustment: bool = False,
    quantity_adjustment_reason: str | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source, request_path, request = latest_valid_30x_report_and_request(reports_dir)
    evidence: dict[str, Any] = {}
    if execution_evidence_json:
        loaded = load_json(execution_evidence_json)
        evidence = dict(_mapping(loaded))
    elif operator_executed:
        source_status = evaluate_source_30x_submit_request(source, request, source_report_path=str(source_path) if source_path else None, submit_request_path=str(request_path) if request_path else None)
        evidence = build_manual_execution_evidence(
            source_status,
            operator_id=operator_id,
            exchange_order_id=exchange_order_id,
            client_order_id=client_order_id,
            filled_quantity=filled_quantity,
            avg_fill_price=avg_fill_price,
            account_position_delta_qty=account_position_delta_qty,
            ledger_event_id=ledger_event_id,
            ledger_filled_quantity=ledger_filled_quantity,
            ledger_notional_usd=ledger_notional_usd,
            emergency_stop_armed=emergency_stop_armed,
            allow_min_notional_quantity_adjustment=allow_min_notional_quantity_adjustment,
            quantity_adjustment_reason=quantity_adjustment_reason,
        )
    return build_live_real_micro_canary_reconciliation_snapshot(
        resolved_settings,
        source,
        request,
        evidence,
        source_report_path=str(source_path) if source_path else None,
        submit_request_path=str(request_path) if request_path else None,
    )


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    if payload.get("decision") == READY_DECISION:
        suffix = "ready"
    elif payload.get("decision") == EXECUTION_EVIDENCE_REQUIRED_DECISION:
        suffix = "execution_evidence_required"
    else:
        suffix = "not_ready"
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, payload)
    exec_ev = _mapping(payload.get("execution_evidence"))
    rec = _mapping(payload.get("reconciliation"))
    emergency = _mapping(payload.get("emergency_stop"))
    lines = [
        f"# {CONTRACT_VERSION} Live-Real Micro Canary Reconciliation",
        "",
        "Consumes 30X submit request and reconciles externally executed live-real micro-canary evidence.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_live_real_micro_canary_reconciliation`: `{payload.get('approved_for_live_real_micro_canary_reconciliation')}`",
        f"- `approved_for_post_canary_review`: `{payload.get('approved_for_post_canary_review')}`",
        f"- `approved_for_additional_exchange_submit`: `{payload.get('approved_for_additional_exchange_submit')}`",
        f"- `approved_for_live_real_continuation`: `{payload.get('approved_for_live_real_continuation')}`",
        f"- `source_30x_submit_request_verified`: `{payload.get('source_30x_submit_request_verified')}`",
        f"- `execution_evidence_verified`: `{payload.get('execution_evidence_verified')}`",
        f"- `mismatch_count`: `{payload.get('mismatch_count')}`",
        f"- `emergency_stop_armed_verified`: `{payload.get('emergency_stop_armed_verified')}`",
        f"- `patch_network_submit_attempted`: `{payload.get('patch_network_submit_attempted')}`",
        f"- `external_exchange_submit_performed`: `{payload.get('external_exchange_submit_performed')}`",
        "",
        "## Execution evidence",
        f"- `operator_id`: `{exec_ev.get('operator_id')}`",
        f"- `exchange_order_id`: `{exec_ev.get('exchange_order_id')}`",
        f"- `client_order_id`: `{exec_ev.get('client_order_id')}`",
        f"- `symbol`: `{exec_ev.get('symbol')}`",
        f"- `side`: `{exec_ev.get('side')}`",
        f"- `status`: `{exec_ev.get('status')}`",
        f"- `filled_quantity`: `{exec_ev.get('filled_quantity')}`",
        f"- `avg_fill_price`: `{exec_ev.get('avg_fill_price')}`",
        f"- `fill_notional_usd`: `{exec_ev.get('fill_notional_usd')}`",
        "",
        "## Reconciliation",
        f"- `request_execution_match`: `{rec.get('request_execution_match')}`",
        f"- `manual_min_notional_quantity_adjustment_requested`: `{rec.get('manual_min_notional_quantity_adjustment_requested')}`",
        f"- `manual_min_notional_quantity_adjustment_accepted`: `{rec.get('manual_min_notional_quantity_adjustment_accepted')}`",
        f"- `manual_min_notional_quantity_adjustment_reason`: `{rec.get('manual_min_notional_quantity_adjustment_reason')}`",
        f"- `account_reconciliation_match`: `{rec.get('account_reconciliation_match')}`",
        f"- `ledger_reconciliation_match`: `{rec.get('ledger_reconciliation_match')}`",
        f"- `ledger_event_id`: `{rec.get('ledger_event_id')}`",
        "",
        "## Emergency stop",
        f"- `emergency_stop_armed`: `{emergency.get('emergency_stop_armed')}`",
        f"- `kill_switch_armed`: `{emergency.get('kill_switch_armed')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
