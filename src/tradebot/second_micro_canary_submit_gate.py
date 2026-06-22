from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, getcontext
from pathlib import Path
from typing import Any, Mapping

try:
    from .config import Settings
except Exception:  # pragma: no cover - isolated tooling fallback
    class Settings:  # type: ignore[no-redef]
        second_micro_canary_submit_gate_enabled: bool = True
        second_micro_canary_submit_gate_no_live_submit_required: bool = True
        second_micro_canary_submit_gate_finalization_token: str = "FINALIZE_32B_SECOND_MICRO_CANARY_SUBMIT_GATE"
        second_micro_canary_submit_gate_default_min_notional_usdt: float = 4.95
        second_micro_canary_submit_gate_default_quantity_step: str = "0.0001"
        second_micro_canary_submit_gate_default_min_quantity: str = "0.0001"

getcontext().prec = 28

CONTRACT_VERSION = "4B.4.3.6.6.32B"
SOURCE_32A_CONTRACT_VERSION = "4B.4.3.6.6.32A"
SOURCE_32A_READY_DECISION = "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_READY_SECOND_MICRO_CANARY_ELIGIBILITY_GATE_NO_LIVE_ORDER_SUBMIT"
REPORT_TYPE = "second_micro_canary_submit_gate"
REPORT_PREFIX = "4B436632B_second_micro_canary_submit_gate"
SOURCE_32A_REPORT_PREFIX = "4B436632A_post_freeze_release_candidate_review"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
FINALIZATION_TOKEN = "FINALIZE_32B_SECOND_MICRO_CANARY_SUBMIT_GATE"

READY_DECISION = "SECOND_MICRO_CANARY_SUBMIT_GATE_READY_SUBMIT_REQUEST_EVIDENCE_NO_LIVE_ORDER_SUBMIT"
SOURCE_32A_REQUIRED_DECISION = "SECOND_MICRO_CANARY_SUBMIT_GATE_32A_READY_REQUIRED_NO_LIVE_ORDER_SUBMIT"
SIZING_REQUIRED_DECISION = "SECOND_MICRO_CANARY_SUBMIT_GATE_MIN_NOTIONAL_SIZING_REQUIRED_NO_LIVE_ORDER_SUBMIT"
OPERATOR_APPROVAL_REQUIRED_DECISION = "SECOND_MICRO_CANARY_SUBMIT_GATE_OPERATOR_APPROVAL_REQUIRED_NO_LIVE_ORDER_SUBMIT"
NOT_READY_DECISION = "SECOND_MICRO_CANARY_SUBMIT_GATE_NOT_READY_NO_LIVE_ORDER_SUBMIT"

DEFAULT_SYMBOL = "ETHUSDT"
DEFAULT_SIDE = "BUY"
DEFAULT_ORDER_TYPE = "MARKET"
DEFAULT_EXCHANGE_MIN_NOTIONAL_USDT = Decimal("4.95")
DEFAULT_QUANTITY_STEP = Decimal("0.0001")
DEFAULT_MIN_QUANTITY = Decimal("0.0001")

RISK_FLAGS: dict[str, bool] = {
    "second_micro_canary_submit_gate_only": True,
    "submit_request_evidence_only": True,
    "no_live_order_submit_contract": True,
    "no_automatic_submit_by_default": True,
    "approved_for_exchange_submit": False,
    "approved_for_additional_exchange_submit": False,
    "approved_for_live_real_order": False,
    "approved_for_second_micro_canary_order_submit": False,
    "patch_exchange_submit_performed": False,
    "patch_network_submit_attempted": False,
    "patch_live_real_order_performed": False,
    "additional_exchange_submit_performed": False,
    "additional_network_submit_attempted": False,
    "additional_live_real_order_performed": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source32AStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    source_31b_release_hygiene_verified: bool
    final_audit_snapshot_reviewed: bool
    capital_cap_confirmed: bool
    capital_cap_usdt: float | None
    second_micro_canary_eligible_candidate: bool
    second_micro_max_notional_usdt: float | None
    daily_loss_limit_usdt: float | None
    max_slippage_bps: float | None
    emergency_stop_armed_verified: bool
    approved_for_live_real_order: bool
    approved_for_second_micro_canary_order_submit: bool
    approved_for_exchange_submit: bool
    approved_for_additional_exchange_submit: bool
    patch_network_submit_attempted: bool
    patch_exchange_submit_performed: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MinNotionalSizingStatus:
    ok: bool
    symbol: str
    side: str
    order_type: str
    reference_price: float | None
    requested_notional_usdt: float | None
    exchange_min_notional_usdt: float | None
    quantity_step: str | None
    min_quantity: str | None
    candidate_quantity: str | None
    candidate_notional_usdt: float | None
    capital_cap_usdt: float | None
    second_micro_max_notional_usdt: float | None
    daily_loss_limit_usdt: float | None
    max_slippage_bps: float | None
    min_notional_sizing_verified: bool
    candidate_within_capital_cap: bool
    candidate_within_second_micro_cap: bool
    candidate_meets_min_notional: bool
    candidate_meets_min_quantity: bool
    quantity_step_verified: bool
    fail_closed_if_min_notional_exceeds_cap: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorSubmitGateStatus:
    ok: bool
    operator_id: str | None
    finalization_token_verified: bool
    emergency_stop_armed: bool
    operator_approve_submit_request: bool
    operator_approval_id: str | None
    audit_comment: str | None
    no_live_order_submit_confirmed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SecondMicroCanarySubmitGateSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_submit_request_evidence: bool
    approved_for_exchange_submit: bool
    approved_for_additional_exchange_submit: bool
    approved_for_live_real_order: bool
    approved_for_second_micro_canary_order_submit: bool
    source_32a_release_candidate_review_verified: bool
    capital_cap_usdt: float | None
    second_micro_max_notional_usdt: float | None
    daily_loss_limit_usdt: float | None
    max_slippage_bps: float | None
    min_notional_sizing_verified: bool
    candidate_symbol: str
    candidate_side: str
    candidate_order_type: str
    candidate_quantity: str | None
    candidate_estimated_notional_usdt: float | None
    exchange_min_notional_usdt: float | None
    reference_price: float | None
    emergency_stop_armed_verified: bool
    operator_submit_request_approval_verified: bool
    submit_request_evidence_created: bool
    submit_request_must_not_be_submitted_by_32b: bool
    no_live_order_submit_verified: bool
    no_code_path_live_submit_verified: bool
    patch_exchange_submit_performed: bool
    patch_network_submit_attempted: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    reason_codes: list[str]
    submit_request: dict[str, Any] | None
    source_32a: dict[str, Any]
    min_notional_sizing: dict[str, Any]
    operator_submit_gate: dict[str, Any]
    source_32a_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


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


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _decimal_to_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    formatted = format(value.normalize(), "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted or "0"


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


def evaluate_source_32a_release_candidate(source_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source32AStatus:
    contract = str(source_snapshot.get("contract_version") or "") or None
    decision = str(source_snapshot.get("decision") or "") or None
    source_31b = _boolish(source_snapshot.get("source_31b_release_hygiene_verified"), False)
    audit_reviewed = _boolish(source_snapshot.get("final_audit_snapshot_reviewed"), False)
    capital_confirmed = _boolish(source_snapshot.get("capital_cap_confirmed"), False)
    capital_cap = _float_or_none(source_snapshot.get("capital_cap_usdt"))
    second_cap = _float_or_none(source_snapshot.get("second_micro_max_notional_usdt"))
    daily_loss = _float_or_none(source_snapshot.get("daily_loss_limit_usdt"))
    slippage = _float_or_none(source_snapshot.get("max_slippage_bps"))
    second_candidate = _boolish(source_snapshot.get("second_micro_canary_eligible_candidate"), False)
    emergency = _boolish(source_snapshot.get("emergency_stop_armed_verified"), False)

    approved_live = _boolish(source_snapshot.get("approved_for_live_real_order"), False)
    approved_second_order = _boolish(source_snapshot.get("approved_for_second_micro_canary_order_submit"), False)
    approved_exchange = _boolish(source_snapshot.get("approved_for_exchange_submit"), False)
    approved_additional = _boolish(source_snapshot.get("approved_for_additional_exchange_submit"), False)
    network = _boolish(source_snapshot.get("patch_network_submit_attempted"), False)
    exchange = _boolish(source_snapshot.get("patch_exchange_submit_performed"), False)
    live = _boolish(source_snapshot.get("patch_live_real_order_performed"), False)
    add_exchange = _boolish(source_snapshot.get("additional_exchange_submit_performed"), False)
    add_network = _boolish(source_snapshot.get("additional_network_submit_attempted"), False)
    add_live = _boolish(source_snapshot.get("additional_live_real_order_performed"), False)

    reason_codes: list[str] = []
    if contract != SOURCE_32A_CONTRACT_VERSION:
        reason_codes.append("SOURCE_32A_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_32A_READY_DECISION:
        reason_codes.append("SOURCE_32A_READY_DECISION_REQUIRED")
    if not source_31b:
        reason_codes.append("SOURCE_31B_RELEASE_HYGIENE_REQUIRED")
    if not audit_reviewed:
        reason_codes.append("FINAL_AUDIT_SNAPSHOT_REVIEW_REQUIRED")
    if not capital_confirmed or capital_cap is None or capital_cap <= 0:
        reason_codes.append("CAPITAL_CAP_CONFIRMATION_REQUIRED")
    if not second_candidate:
        reason_codes.append("SECOND_MICRO_CANARY_ELIGIBILITY_CANDIDATE_REQUIRED")
    if second_cap is None or second_cap <= 0:
        reason_codes.append("SECOND_MICRO_MAX_NOTIONAL_REQUIRED")
    if daily_loss is None or daily_loss <= 0:
        reason_codes.append("DAILY_LOSS_LIMIT_REQUIRED")
    if slippage is None or slippage <= 0:
        reason_codes.append("MAX_SLIPPAGE_LIMIT_REQUIRED")
    if not emergency:
        reason_codes.append("SOURCE_32A_EMERGENCY_STOP_REQUIRED")
    if approved_live or approved_second_order or approved_exchange or approved_additional:
        reason_codes.append("SOURCE_32A_MUST_NOT_APPROVE_LIVE_OR_EXCHANGE_SUBMIT")
    if network or exchange or live or add_exchange or add_network or add_live:
        reason_codes.append("SOURCE_32A_MUST_HAVE_NO_SUBMIT_ACTIVITY")

    return Source32AStatus(
        ok=not reason_codes,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        source_31b_release_hygiene_verified=source_31b,
        final_audit_snapshot_reviewed=audit_reviewed,
        capital_cap_confirmed=capital_confirmed,
        capital_cap_usdt=capital_cap,
        second_micro_canary_eligible_candidate=second_candidate,
        second_micro_max_notional_usdt=second_cap,
        daily_loss_limit_usdt=daily_loss,
        max_slippage_bps=slippage,
        emergency_stop_armed_verified=emergency,
        approved_for_live_real_order=approved_live,
        approved_for_second_micro_canary_order_submit=approved_second_order,
        approved_for_exchange_submit=approved_exchange,
        approved_for_additional_exchange_submit=approved_additional,
        patch_network_submit_attempted=network,
        patch_exchange_submit_performed=exchange,
        patch_live_real_order_performed=live,
        additional_exchange_submit_performed=add_exchange,
        additional_network_submit_attempted=add_network,
        additional_live_real_order_performed=add_live,
        reason_codes=reason_codes,
    )


def _ceil_to_step(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_CEILING) * step


def evaluate_min_notional_sizing(
    *,
    symbol: str = DEFAULT_SYMBOL,
    side: str = DEFAULT_SIDE,
    order_type: str = DEFAULT_ORDER_TYPE,
    reference_price: Any,
    requested_notional_usdt: Any = None,
    exchange_min_notional_usdt: Any = DEFAULT_EXCHANGE_MIN_NOTIONAL_USDT,
    quantity_step: Any = DEFAULT_QUANTITY_STEP,
    min_quantity: Any = DEFAULT_MIN_QUANTITY,
    capital_cap_usdt: float | None,
    second_micro_max_notional_usdt: float | None,
    daily_loss_limit_usdt: float | None,
    max_slippage_bps: float | None,
) -> MinNotionalSizingStatus:
    reason_codes: list[str] = []
    normalized_symbol = str(symbol or "").upper().strip()
    normalized_side = str(side or "").upper().strip()
    normalized_order_type = str(order_type or "").upper().strip()

    price = _decimal_or_none(reference_price)
    requested = _decimal_or_none(requested_notional_usdt)
    min_notional = _decimal_or_none(exchange_min_notional_usdt)
    step = _decimal_or_none(quantity_step)
    min_qty = _decimal_or_none(min_quantity)
    capital_cap = _decimal_or_none(capital_cap_usdt)
    second_cap = _decimal_or_none(second_micro_max_notional_usdt)

    if not normalized_symbol:
        reason_codes.append("SYMBOL_REQUIRED")
    if normalized_side not in {"BUY", "SELL"}:
        reason_codes.append("SIDE_REQUIRED_BUY_OR_SELL")
    if normalized_order_type not in {"MARKET"}:
        reason_codes.append("ORDER_TYPE_MARKET_ONLY_FOR_MICRO_CANARY")
    if price is None or price <= 0:
        reason_codes.append("REFERENCE_PRICE_REQUIRED_POSITIVE")
    if min_notional is None or min_notional <= 0:
        reason_codes.append("EXCHANGE_MIN_NOTIONAL_REQUIRED_POSITIVE")
    if step is None or step <= 0:
        reason_codes.append("QUANTITY_STEP_REQUIRED_POSITIVE")
    if min_qty is None or min_qty <= 0:
        reason_codes.append("MIN_QUANTITY_REQUIRED_POSITIVE")
    if capital_cap is None or capital_cap <= 0:
        reason_codes.append("CAPITAL_CAP_REQUIRED_POSITIVE")
    if second_cap is None or second_cap <= 0:
        reason_codes.append("SECOND_MICRO_MAX_NOTIONAL_REQUIRED_POSITIVE")
    if daily_loss_limit_usdt is None or daily_loss_limit_usdt <= 0:
        reason_codes.append("DAILY_LOSS_LIMIT_REQUIRED_POSITIVE")
    if max_slippage_bps is None or max_slippage_bps <= 0:
        reason_codes.append("MAX_SLIPPAGE_BPS_REQUIRED_POSITIVE")
    if requested is not None and requested <= 0:
        reason_codes.append("REQUESTED_NOTIONAL_REQUIRED_POSITIVE_IF_PROVIDED")

    candidate_qty: Decimal | None = None
    candidate_notional: Decimal | None = None
    if not reason_codes and price is not None and min_notional is not None and step is not None and min_qty is not None:
        target_notional = requested if requested is not None else min_notional
        if target_notional < min_notional:
            target_notional = min_notional
        raw_qty = target_notional / price
        stepped = _ceil_to_step(raw_qty, step)
        candidate_qty = max(stepped, min_qty)
        candidate_notional = candidate_qty * price
        if candidate_qty <= 0:
            reason_codes.append("CANDIDATE_QUANTITY_REQUIRED_POSITIVE")
        if candidate_notional < min_notional:
            reason_codes.append("CANDIDATE_NOTIONAL_BELOW_EXCHANGE_MIN_NOTIONAL")
        if requested is not None and second_cap is not None and requested > second_cap:
            reason_codes.append("REQUESTED_NOTIONAL_EXCEEDS_SECOND_MICRO_CAP")
        if second_cap is not None and candidate_notional > second_cap:
            reason_codes.append("CANDIDATE_NOTIONAL_EXCEEDS_SECOND_MICRO_CAP_FAIL_CLOSED")
        if capital_cap is not None and candidate_notional > capital_cap:
            reason_codes.append("CANDIDATE_NOTIONAL_EXCEEDS_CAPITAL_CAP_FAIL_CLOSED")
        if min_notional is not None and second_cap is not None and min_notional > second_cap:
            reason_codes.append("EXCHANGE_MIN_NOTIONAL_EXCEEDS_SECOND_MICRO_CAP_FAIL_CLOSED")
        if step is not None and candidate_qty % step != 0:
            reason_codes.append("CANDIDATE_QUANTITY_STEP_MISMATCH")

    candidate_within_cap = bool(candidate_notional is not None and capital_cap is not None and candidate_notional <= capital_cap)
    candidate_within_second = bool(candidate_notional is not None and second_cap is not None and candidate_notional <= second_cap)
    meets_min_notional = bool(candidate_notional is not None and min_notional is not None and candidate_notional >= min_notional)
    meets_min_quantity = bool(candidate_qty is not None and min_qty is not None and candidate_qty >= min_qty)
    quantity_step_ok = bool(candidate_qty is not None and step is not None and candidate_qty % step == 0)

    return MinNotionalSizingStatus(
        ok=not reason_codes,
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_order_type,
        reference_price=_decimal_to_float(price),
        requested_notional_usdt=_decimal_to_float(requested),
        exchange_min_notional_usdt=_decimal_to_float(min_notional),
        quantity_step=_decimal_to_str(step),
        min_quantity=_decimal_to_str(min_qty),
        candidate_quantity=_decimal_to_str(candidate_qty),
        candidate_notional_usdt=_decimal_to_float(candidate_notional),
        capital_cap_usdt=capital_cap_usdt,
        second_micro_max_notional_usdt=second_micro_max_notional_usdt,
        daily_loss_limit_usdt=daily_loss_limit_usdt,
        max_slippage_bps=max_slippage_bps,
        min_notional_sizing_verified=not reason_codes,
        candidate_within_capital_cap=candidate_within_cap,
        candidate_within_second_micro_cap=candidate_within_second,
        candidate_meets_min_notional=meets_min_notional,
        candidate_meets_min_quantity=meets_min_quantity,
        quantity_step_verified=quantity_step_ok,
        fail_closed_if_min_notional_exceeds_cap=True,
        reason_codes=reason_codes,
    )


def evaluate_operator_submit_gate(
    *,
    operator_id: str | None,
    finalization_token: str | None,
    emergency_stop_armed: bool,
    operator_approve_submit_request: bool,
    operator_approval_id: str | None = None,
    audit_comment: str | None = None,
) -> OperatorSubmitGateStatus:
    reason_codes: list[str] = []
    if not operator_id:
        reason_codes.append("OPERATOR_ID_REQUIRED")
    if finalization_token != FINALIZATION_TOKEN:
        reason_codes.append("FINALIZATION_TOKEN_REQUIRED")
    if not emergency_stop_armed:
        reason_codes.append("EMERGENCY_STOP_ARMED_REQUIRED")
    if not operator_approve_submit_request:
        reason_codes.append("OPERATOR_APPROVE_SUBMIT_REQUEST_REQUIRED")
    if not operator_approval_id:
        reason_codes.append("OPERATOR_APPROVAL_ID_REQUIRED")
    return OperatorSubmitGateStatus(
        ok=not reason_codes,
        operator_id=operator_id,
        finalization_token_verified=finalization_token == FINALIZATION_TOKEN,
        emergency_stop_armed=bool(emergency_stop_armed),
        operator_approve_submit_request=bool(operator_approve_submit_request),
        operator_approval_id=operator_approval_id,
        audit_comment=audit_comment,
        no_live_order_submit_confirmed=True,
        reason_codes=reason_codes,
    )


def _candidate_id(*, source_report_path: str | None, symbol: str, side: str, quantity: str | None, notional: float | None) -> str:
    material = json.dumps(
        {
            "contract_version": CONTRACT_VERSION,
            "source_report_path": source_report_path,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "notional": notional,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _submit_request(*, source_status: Source32AStatus, sizing: MinNotionalSizingStatus) -> dict[str, Any]:
    return {
        "candidate_request_id": _candidate_id(
            source_report_path=source_status.source_report_path,
            symbol=sizing.symbol,
            side=sizing.side,
            quantity=sizing.candidate_quantity,
            notional=sizing.candidate_notional_usdt,
        ),
        "contract_version": CONTRACT_VERSION,
        "source_contract_version": SOURCE_32A_CONTRACT_VERSION,
        "source_32a_report_path": source_status.source_report_path,
        "symbol": sizing.symbol,
        "side": sizing.side,
        "type": sizing.order_type,
        "quantity": sizing.candidate_quantity,
        "estimated_notional_usdt": sizing.candidate_notional_usdt,
        "reference_price": sizing.reference_price,
        "requested_notional_usdt": sizing.requested_notional_usdt,
        "exchange_min_notional_usdt": sizing.exchange_min_notional_usdt,
        "quantity_step": sizing.quantity_step,
        "min_quantity": sizing.min_quantity,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "must_not_be_submitted_by_32b": True,
        "requires_separate_32c_live_submit_phase": True,
    }


def build_snapshot(
    *,
    source_snapshot: Mapping[str, Any],
    source_report_path: str | None,
    operator_id: str | None,
    finalization_token: str | None,
    emergency_stop_armed: bool,
    operator_approve_submit_request: bool,
    operator_approval_id: str | None,
    audit_comment: str | None,
    symbol: str,
    side: str,
    order_type: str,
    reference_price: Any,
    requested_notional_usdt: Any = None,
    exchange_min_notional_usdt: Any = DEFAULT_EXCHANGE_MIN_NOTIONAL_USDT,
    quantity_step: Any = DEFAULT_QUANTITY_STEP,
    min_quantity: Any = DEFAULT_MIN_QUANTITY,
) -> dict[str, Any]:
    source_status = evaluate_source_32a_release_candidate(source_snapshot, source_report_path=source_report_path)
    sizing = evaluate_min_notional_sizing(
        symbol=symbol,
        side=side,
        order_type=order_type,
        reference_price=reference_price,
        requested_notional_usdt=requested_notional_usdt,
        exchange_min_notional_usdt=exchange_min_notional_usdt,
        quantity_step=quantity_step,
        min_quantity=min_quantity,
        capital_cap_usdt=source_status.capital_cap_usdt,
        second_micro_max_notional_usdt=source_status.second_micro_max_notional_usdt,
        daily_loss_limit_usdt=source_status.daily_loss_limit_usdt,
        max_slippage_bps=source_status.max_slippage_bps,
    )
    operator = evaluate_operator_submit_gate(
        operator_id=operator_id,
        finalization_token=finalization_token,
        emergency_stop_armed=emergency_stop_armed,
        operator_approve_submit_request=operator_approve_submit_request,
        operator_approval_id=operator_approval_id,
        audit_comment=audit_comment,
    )

    reason_codes: list[str] = []
    if not source_status.ok:
        reason_codes.extend(source_status.reason_codes)
        decision = SOURCE_32A_REQUIRED_DECISION
    elif not sizing.ok:
        reason_codes.extend(sizing.reason_codes)
        decision = SIZING_REQUIRED_DECISION
    elif not operator.ok:
        reason_codes.extend(operator.reason_codes)
        decision = OPERATOR_APPROVAL_REQUIRED_DECISION
    else:
        decision = READY_DECISION

    ready = decision == READY_DECISION
    submit_request = _submit_request(source_status=source_status, sizing=sizing) if ready else None
    snapshot = SecondMicroCanarySubmitGateSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_32A_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_submit_request_evidence=ready,
        approved_for_exchange_submit=False,
        approved_for_additional_exchange_submit=False,
        approved_for_live_real_order=False,
        approved_for_second_micro_canary_order_submit=False,
        source_32a_release_candidate_review_verified=source_status.ok,
        capital_cap_usdt=source_status.capital_cap_usdt,
        second_micro_max_notional_usdt=source_status.second_micro_max_notional_usdt,
        daily_loss_limit_usdt=source_status.daily_loss_limit_usdt,
        max_slippage_bps=source_status.max_slippage_bps,
        min_notional_sizing_verified=sizing.ok,
        candidate_symbol=sizing.symbol,
        candidate_side=sizing.side,
        candidate_order_type=sizing.order_type,
        candidate_quantity=sizing.candidate_quantity if ready else None,
        candidate_estimated_notional_usdt=sizing.candidate_notional_usdt if ready else None,
        exchange_min_notional_usdt=sizing.exchange_min_notional_usdt,
        reference_price=sizing.reference_price,
        emergency_stop_armed_verified=operator.emergency_stop_armed and source_status.emergency_stop_armed_verified,
        operator_submit_request_approval_verified=operator.ok,
        submit_request_evidence_created=ready,
        submit_request_must_not_be_submitted_by_32b=True,
        no_live_order_submit_verified=True,
        no_code_path_live_submit_verified=True,
        patch_exchange_submit_performed=False,
        patch_network_submit_attempted=False,
        patch_live_real_order_performed=False,
        additional_exchange_submit_performed=False,
        additional_network_submit_attempted=False,
        additional_live_real_order_performed=False,
        reason_codes=reason_codes,
        submit_request=submit_request,
        source_32a=source_status.to_dict(),
        min_notional_sizing=sizing.to_dict(),
        operator_submit_gate=operator.to_dict(),
        source_32a_snapshot=dict(source_snapshot),
    )
    payload = snapshot.to_dict()
    payload.update(RISK_FLAGS)
    return payload


def _iter_source_32a_reports(reports_dir: str | os.PathLike[str]) -> list[Path]:
    root = Path(reports_dir)
    if not root.exists():
        return []
    candidates = [
        path for path in root.glob(f"{SOURCE_32A_REPORT_PREFIX}_*_ready.json")
        if path.is_file() and not path.name.endswith("_not_ready.json")
    ]
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def build_from_explicit_32a_report(
    *,
    reports_dir: str | os.PathLike[str],
    source_32a_report: str | os.PathLike[str],
    operator_id: str | None,
    finalization_token: str | None,
    emergency_stop_armed: bool,
    operator_approve_submit_request: bool,
    operator_approval_id: str | None,
    audit_comment: str | None = None,
    symbol: str = DEFAULT_SYMBOL,
    side: str = DEFAULT_SIDE,
    order_type: str = DEFAULT_ORDER_TYPE,
    reference_price: Any = None,
    requested_notional_usdt: Any = None,
    exchange_min_notional_usdt: Any = DEFAULT_EXCHANGE_MIN_NOTIONAL_USDT,
    quantity_step: Any = DEFAULT_QUANTITY_STEP,
    min_quantity: Any = DEFAULT_MIN_QUANTITY,
) -> dict[str, Any]:
    path = Path(source_32a_report)
    source = _mapping(load_json(path)) if path.exists() else {}
    return build_snapshot(
        source_snapshot=source,
        source_report_path=str(path),
        operator_id=operator_id,
        finalization_token=finalization_token,
        emergency_stop_armed=emergency_stop_armed,
        operator_approve_submit_request=operator_approve_submit_request,
        operator_approval_id=operator_approval_id,
        audit_comment=audit_comment,
        symbol=symbol,
        side=side,
        order_type=order_type,
        reference_price=reference_price,
        requested_notional_usdt=requested_notional_usdt,
        exchange_min_notional_usdt=exchange_min_notional_usdt,
        quantity_step=quantity_step,
        min_quantity=min_quantity,
    )


def build_from_latest_32a_report(
    *,
    reports_dir: str | os.PathLike[str],
    operator_id: str | None,
    finalization_token: str | None,
    emergency_stop_armed: bool,
    operator_approve_submit_request: bool,
    operator_approval_id: str | None,
    audit_comment: str | None = None,
    symbol: str = DEFAULT_SYMBOL,
    side: str = DEFAULT_SIDE,
    order_type: str = DEFAULT_ORDER_TYPE,
    reference_price: Any = None,
    requested_notional_usdt: Any = None,
    exchange_min_notional_usdt: Any = DEFAULT_EXCHANGE_MIN_NOTIONAL_USDT,
    quantity_step: Any = DEFAULT_QUANTITY_STEP,
    min_quantity: Any = DEFAULT_MIN_QUANTITY,
) -> dict[str, Any]:
    candidates = _iter_source_32a_reports(reports_dir)
    if not candidates:
        return build_snapshot(
            source_snapshot={},
            source_report_path=None,
            operator_id=operator_id,
            finalization_token=finalization_token,
            emergency_stop_armed=emergency_stop_armed,
            operator_approve_submit_request=operator_approve_submit_request,
            operator_approval_id=operator_approval_id,
            audit_comment=audit_comment,
            symbol=symbol,
            side=side,
            order_type=order_type,
            reference_price=reference_price,
            requested_notional_usdt=requested_notional_usdt,
            exchange_min_notional_usdt=exchange_min_notional_usdt,
            quantity_step=quantity_step,
            min_quantity=min_quantity,
        )
    return build_from_explicit_32a_report(
        reports_dir=reports_dir,
        source_32a_report=candidates[0],
        operator_id=operator_id,
        finalization_token=finalization_token,
        emergency_stop_armed=emergency_stop_armed,
        operator_approve_submit_request=operator_approve_submit_request,
        operator_approval_id=operator_approval_id,
        audit_comment=audit_comment,
        symbol=symbol,
        side=side,
        order_type=order_type,
        reference_price=reference_price,
        requested_notional_usdt=requested_notional_usdt,
        exchange_min_notional_usdt=exchange_min_notional_usdt,
        quantity_step=quantity_step,
        min_quantity=min_quantity,
    )


def write_report_bundle(payload: Mapping[str, Any], *, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, dict(payload))
    md = [
        f"# {CONTRACT_VERSION} Second Micro-Canary Submit Gate",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- source_32a_release_candidate_review_verified: `{payload.get('source_32a_release_candidate_review_verified')}`",
        f"- min_notional_sizing_verified: `{payload.get('min_notional_sizing_verified')}`",
        f"- operator_submit_request_approval_verified: `{payload.get('operator_submit_request_approval_verified')}`",
        f"- candidate_symbol: `{payload.get('candidate_symbol')}`",
        f"- candidate_quantity: `{payload.get('candidate_quantity')}`",
        f"- candidate_estimated_notional_usdt: `{payload.get('candidate_estimated_notional_usdt')}`",
        f"- approved_for_exchange_submit: `{payload.get('approved_for_exchange_submit')}`",
        f"- approved_for_second_micro_canary_order_submit: `{payload.get('approved_for_second_micro_canary_order_submit')}`",
        f"- patch_network_submit_attempted: `{payload.get('patch_network_submit_attempted')}`",
        "",
        "## Risk note",
        "",
        "32B creates submit-request evidence only. It must not submit an exchange order. A separate 32C live-submit phase is required for any real order.",
        "",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")
    return json_path, md_path
