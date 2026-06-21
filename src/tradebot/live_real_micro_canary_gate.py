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

CONTRACT_VERSION = "4B.4.3.6.6.30X"
SOURCE_30W_CONTRACT_VERSION = "4B.4.3.6.6.30W"
SOURCE_30W_READY_DECISION = "LIVE_REAL_FINAL_OPERATOR_APPROVAL_READY_FINAL_APPROVAL_CAPTURED_SUBMIT_BLOCKED_UNTIL_30X_NO_LIVE_REAL_ORDER"
REPORT_TYPE = "first_live_real_micro_canary_single_min_size_gate"
REPORT_PREFIX = "4B436630X_first_live_real_micro_canary"
SUBMIT_REQUEST_FILENAME = "4B436630X_first_live_real_micro_canary_submit_request.json"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

APPROVAL_TOKEN = "APPROVE_FIRST_LIVE_REAL_MICRO_CANARY"
READY_DECISION = "FIRST_LIVE_REAL_MICRO_CANARY_GATE_READY_SINGLE_MIN_SIZE_SUBMIT_REQUEST_BUILT_NO_AUTOMATED_NETWORK_SUBMIT"
OPERATOR_APPROVAL_REQUIRED_DECISION = "FIRST_LIVE_REAL_MICRO_CANARY_GATE_OPERATOR_APPROVAL_REQUIRED_NO_NETWORK_SUBMIT"
SOURCE_30W_REQUIRED_DECISION = "FIRST_LIVE_REAL_MICRO_CANARY_GATE_30W_FINAL_APPROVAL_REQUIRED_NO_NETWORK_SUBMIT"
ORDER_REQUEST_NOT_READY_DECISION = "FIRST_LIVE_REAL_MICRO_CANARY_GATE_ORDER_REQUEST_NOT_READY_NO_NETWORK_SUBMIT"
CAPS_NOT_READY_DECISION = "FIRST_LIVE_REAL_MICRO_CANARY_GATE_HARD_CAPS_OR_KILL_SWITCH_NOT_READY_NO_NETWORK_SUBMIT"
NOT_READY_DECISION = "FIRST_LIVE_REAL_MICRO_CANARY_GATE_NOT_READY_NO_NETWORK_SUBMIT"

RISK_FLAGS: dict[str, bool] = {
    "micro_canary_only": True,
    "single_order_gate_only": True,
    "manual_runtime_handoff_only": True,
    "automated_network_submit_disabled": True,
    "live_real_micro_canary_gate": True,
    "live_real_order_performed": False,
    "live_real_order_submitted": False,
    "live_real_network_submit_attempted": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "exchange_submit_performed": False,
    "network_submit_attempted": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30WFinalApprovalStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    final_operator_approval_ready: bool
    micro_canary_candidate: bool
    final_operator_approval_verified: bool
    submit_blocked_until_30x: bool
    hard_live_submit_block_verified: bool
    no_exchange_submit_verified: bool
    no_live_real_order_verified: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    trading_action_performed: bool
    order_actions_performed: bool
    live_real_order_performed: bool
    live_real_order_submitted: bool
    live_real_network_submit_attempted: bool
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    total_notional_usd: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MicroCanaryApprovalStatus:
    ok: bool
    required: bool
    issued: bool
    operator_id: str | None
    approval_token_expected: str
    approval_token_matched: bool
    operator_id_required: bool
    captured_at_utc: str | None
    no_secret_material_persisted: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MicroCanaryOrderRequestStatus:
    ok: bool
    symbol: str
    side: str
    order_type: str
    quantity: float
    mark_price: float
    notional_usd: float
    min_notional_usd: float
    max_notional_usd: float
    leverage: int
    max_leverage: int
    reduce_only: bool
    post_only: bool
    time_in_force: str
    client_order_id: str
    submit_handoff_mode: str
    write_submit_request: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HardCapsStatus:
    ok: bool
    required: bool
    kill_switch_armed: bool
    single_order_cap: int
    exchange_submit_cap: int
    network_submit_cap: int
    request_count: int
    exchange_submit_count: int
    network_submit_count: int
    max_total_notional_usd: float
    requested_notional_usd: float
    automated_network_submit_disabled: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FirstLiveRealMicroCanarySnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_first_live_real_micro_canary_gate: bool
    approved_for_first_live_real_micro_canary_submit_request: bool
    approved_for_manual_runtime_handoff: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    source_30w_final_operator_approval_verified: bool
    micro_canary_operator_approval_verified: bool
    single_min_size_order_request_verified: bool
    hard_caps_verified: bool
    kill_switch_verified: bool
    automated_network_submit_disabled_verified: bool
    submit_request_built: bool
    submit_request_path: str | None
    submit_request_count: int
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    total_notional_usd: float
    max_total_notional_usd: float
    exchange_submit_performed: bool
    network_submit_attempted: bool
    trading_action_performed: bool
    order_actions_performed: bool
    live_real_order_performed: bool
    live_real_order_submitted: bool
    live_real_network_submit_attempted: bool
    runtime_activation_blocked: bool
    training_reload_blocked: bool
    reason_codes: list[str]
    source_30w: dict[str, Any]
    micro_canary_approval: dict[str, Any]
    order_request: dict[str, Any]
    hard_caps: dict[str, Any]
    no_automated_network_submit: dict[str, Any]
    source_30w_snapshot: dict[str, Any]

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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _first_present(mapping: Mapping[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


def _nested(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in (
        "checks",
        "module_probe",
        "source_30w",
        "operator_approval",
        "hard_submit_block",
        "no_exchange_submit",
        "no_live_real_order",
    ):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def evaluate_source_30w_final_approval(source_30w_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30WFinalApprovalStatus:
    nested = _nested(source_30w_snapshot)
    contract = str(source_30w_snapshot.get("contract_version") or "") or None
    decision = str(source_30w_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30W_READY_DECISION
    final_ready = _boolish(_first_present(source_30w_snapshot, ("approved_for_live_real_final_operator_approval",), nested.get("approved_for_live_real_final_operator_approval", decision_ok)), decision_ok)
    candidate = _boolish(_first_present(source_30w_snapshot, ("approved_for_30x_live_real_micro_canary_candidate",), nested.get("approved_for_30x_live_real_micro_canary_candidate", decision_ok)), decision_ok)
    approval_verified = _boolish(_first_present(source_30w_snapshot, ("final_operator_approval_verified",), nested.get("final_operator_approval_verified", decision_ok)), decision_ok)
    blocked_until_30x = _boolish(_first_present(source_30w_snapshot, ("live_real_submit_blocked_until_30x",), nested.get("submit_blocked_until_30x", decision_ok)), decision_ok)
    hard_block = _boolish(_first_present(source_30w_snapshot, ("hard_live_submit_block_verified",), nested.get("hard_live_submit_block_verified", decision_ok)), decision_ok)
    no_exchange = _boolish(_first_present(source_30w_snapshot, ("no_exchange_submit_verified",), nested.get("no_exchange_submit_verified", True)), True)
    no_live_order = _boolish(_first_present(source_30w_snapshot, ("no_live_real_order_verified",), nested.get("no_live_real_order_verified", True)), True)
    approved_exchange = _boolish(_first_present(source_30w_snapshot, ("approved_for_exchange_submit",), nested.get("approved_for_exchange_submit", False)), False)
    approved_live = _boolish(_first_present(source_30w_snapshot, ("approved_for_live_real",), nested.get("approved_for_live_real", False)), False)
    exchange_submit = _boolish(_first_present(source_30w_snapshot, ("exchange_submit_performed",), nested.get("exchange_submit_performed", False)), False)
    network_submit = _boolish(_first_present(source_30w_snapshot, ("network_submit_attempted",), nested.get("network_submit_attempted", False)), False)
    trading = _boolish(_first_present(source_30w_snapshot, ("trading_action_performed",), nested.get("trading_action_performed", False)), False)
    order_actions = _boolish(_first_present(source_30w_snapshot, ("order_actions_performed",), nested.get("order_actions_performed", False)), False)
    live_order = _boolish(_first_present(source_30w_snapshot, ("live_real_order_performed",), nested.get("live_real_order_performed", False)), False)
    live_submitted = _boolish(_first_present(source_30w_snapshot, ("live_real_order_submitted",), nested.get("live_real_order_submitted", False)), False)
    live_network = _boolish(_first_present(source_30w_snapshot, ("live_real_network_submit_attempted",), nested.get("live_real_network_submit_attempted", False)), False)
    order_count = _int(_first_present(source_30w_snapshot, ("order_action_count",), nested.get("order_action_count", 0)), 0)
    exchange_count = _int(_first_present(source_30w_snapshot, ("exchange_submit_count",), nested.get("exchange_submit_count", 0)), 0)
    network_count = _int(_first_present(source_30w_snapshot, ("network_submit_count",), nested.get("network_submit_count", 0)), 0)
    total_notional = _float(_first_present(source_30w_snapshot, ("total_notional_usd",), nested.get("total_notional_usd", 0.0)), 0.0)
    ok = (
        contract == SOURCE_30W_CONTRACT_VERSION
        and decision_ok
        and final_ready
        and candidate
        and approval_verified
        and blocked_until_30x
        and hard_block
        and no_exchange
        and no_live_order
        and not approved_exchange
        and not approved_live
        and not exchange_submit
        and not network_submit
        and not trading
        and not order_actions
        and not live_order
        and not live_submitted
        and not live_network
        and order_count == 0
        and exchange_count == 0
        and network_count == 0
    )
    reasons: list[str] = []
    if contract != SOURCE_30W_CONTRACT_VERSION:
        reasons.append("SOURCE_30W_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30W_READY_DECISION_REQUIRED")
    if not final_ready or not candidate or not approval_verified:
        reasons.append("SOURCE_30W_FINAL_OPERATOR_APPROVAL_NOT_VERIFIED")
    if not blocked_until_30x or not hard_block:
        reasons.append("SOURCE_30W_HARD_BLOCK_UNTIL_30X_NOT_VERIFIED")
    if approved_exchange or approved_live or exchange_submit or network_submit or trading or order_actions or live_order or live_submitted or live_network:
        reasons.append("SOURCE_30W_UNEXPECTED_SUBMIT_OR_ORDER_ACTIVITY")
    if order_count != 0 or exchange_count != 0 or network_count != 0:
        reasons.append("SOURCE_30W_COUNTS_NOT_ZERO")
    return Source30WFinalApprovalStatus(
        ok=ok,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        final_operator_approval_ready=final_ready,
        micro_canary_candidate=candidate,
        final_operator_approval_verified=approval_verified,
        submit_blocked_until_30x=blocked_until_30x,
        hard_live_submit_block_verified=hard_block,
        no_exchange_submit_verified=no_exchange,
        no_live_real_order_verified=no_live_order,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        exchange_submit_performed=exchange_submit,
        network_submit_attempted=network_submit,
        trading_action_performed=trading,
        order_actions_performed=order_actions,
        live_real_order_performed=live_order,
        live_real_order_submitted=live_submitted,
        live_real_network_submit_attempted=live_network,
        order_action_count=order_count,
        exchange_submit_count=exchange_count,
        network_submit_count=network_count,
        total_notional_usd=total_notional,
        reason_codes=reasons or ["SOURCE_30W_FINAL_OPERATOR_APPROVAL_VERIFIED_FOR_30X"],
    )


def evaluate_micro_canary_approval(
    settings: Any,
    *,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_micro_canary_approval: bool = False,
) -> MicroCanaryApprovalStatus:
    required = _boolish(_setting(settings, "live_real_micro_canary_operator_approval_required", True), True)
    operator_required = _boolish(_setting(settings, "live_real_micro_canary_operator_id_required", True), True)
    expected = str(_setting(settings, "live_real_micro_canary_approval_token", APPROVAL_TOKEN) or APPROVAL_TOKEN)
    issued = bool(issue_micro_canary_approval)
    token_ok = bool(approval_token) and approval_token == expected
    operator_ok = bool(operator_id and operator_id.strip()) if operator_required else True
    ok = (not required) or (issued and token_ok and operator_ok)
    reasons: list[str] = []
    if required and not issued:
        reasons.append("MICRO_CANARY_OPERATOR_APPROVAL_NOT_ISSUED")
    if required and not token_ok:
        reasons.append("MICRO_CANARY_APPROVAL_TOKEN_MISMATCH")
    if operator_required and not operator_ok:
        reasons.append("MICRO_CANARY_OPERATOR_ID_REQUIRED")
    return MicroCanaryApprovalStatus(
        ok=ok,
        required=required,
        issued=issued,
        operator_id=operator_id.strip() if operator_id else None,
        approval_token_expected=expected,
        approval_token_matched=token_ok,
        operator_id_required=operator_required,
        captured_at_utc=utc_now_iso() if ok and issued else None,
        no_secret_material_persisted=True,
        reason_codes=reasons or ["MICRO_CANARY_OPERATOR_APPROVAL_VERIFIED"],
    )


def evaluate_order_request(
    settings: Any,
    *,
    symbol: str | None = None,
    side: str | None = None,
    quantity: float | str | None = None,
    mark_price: float | str | None = None,
    write_submit_request: bool = False,
) -> MicroCanaryOrderRequestStatus:
    resolved_symbol = str(symbol or _setting(settings, "live_real_micro_canary_symbol", "ETHUSDT") or "ETHUSDT").strip().upper()
    resolved_side = str(side or _setting(settings, "live_real_micro_canary_side", "BUY") or "BUY").strip().upper()
    order_type = str(_setting(settings, "live_real_micro_canary_order_type", "MARKET") or "MARKET").strip().upper()
    qty = _float(quantity if quantity is not None else _setting(settings, "live_real_micro_canary_quantity", 0.002), 0.0)
    price = _float(mark_price if mark_price is not None else _setting(settings, "live_real_micro_canary_mark_price", 2500.0), 0.0)
    min_notional = _float(_setting(settings, "live_real_micro_canary_min_notional_usd", 5.0), 5.0)
    max_notional = _float(_setting(settings, "live_real_micro_canary_max_notional_usd", 10.0), 10.0)
    leverage = _int(_setting(settings, "live_real_micro_canary_leverage", 1), 1)
    max_leverage = _int(_setting(settings, "live_real_micro_canary_max_leverage", 1), 1)
    reduce_only = _boolish(_setting(settings, "live_real_micro_canary_reduce_only", False), False)
    post_only = _boolish(_setting(settings, "live_real_micro_canary_post_only", False), False)
    tif = str(_setting(settings, "live_real_micro_canary_time_in_force", "IOC") or "IOC").strip().upper()
    handoff = str(_setting(settings, "live_real_micro_canary_submit_handoff_mode", "manual_runtime_only") or "manual_runtime_only")
    notional = qty * price
    client_order_id = f"tbv2-30x-{utc_stamp()}-{resolved_symbol.lower()}"
    ok = (
        bool(resolved_symbol)
        and resolved_side in {"BUY", "SELL"}
        and order_type == "MARKET"
        and qty > 0
        and price > 0
        and min_notional <= notional <= max_notional
        and leverage >= 1
        and leverage <= max_leverage
        and max_leverage <= 1
        and not reduce_only
        and not post_only
        and tif in {"IOC", "GTC"}
        and handoff == "manual_runtime_only"
    )
    reasons: list[str] = []
    if not resolved_symbol:
        reasons.append("MICRO_CANARY_SYMBOL_REQUIRED")
    if resolved_side not in {"BUY", "SELL"}:
        reasons.append("MICRO_CANARY_SIDE_INVALID")
    if order_type != "MARKET":
        reasons.append("MICRO_CANARY_MARKET_ORDER_ONLY")
    if qty <= 0 or price <= 0:
        reasons.append("MICRO_CANARY_QUANTITY_AND_MARK_PRICE_REQUIRED")
    if not (min_notional <= notional <= max_notional):
        reasons.append("MICRO_CANARY_NOTIONAL_OUTSIDE_MIN_MAX_CAPS")
    if leverage < 1 or leverage > max_leverage or max_leverage > 1:
        reasons.append("MICRO_CANARY_LEVERAGE_CAP_VIOLATION")
    if reduce_only or post_only:
        reasons.append("MICRO_CANARY_UNSUPPORTED_ORDER_FLAG")
    if handoff != "manual_runtime_only":
        reasons.append("MICRO_CANARY_MANUAL_RUNTIME_HANDOFF_REQUIRED")
    return MicroCanaryOrderRequestStatus(
        ok=ok,
        symbol=resolved_symbol,
        side=resolved_side,
        order_type=order_type,
        quantity=qty,
        mark_price=price,
        notional_usd=notional,
        min_notional_usd=min_notional,
        max_notional_usd=max_notional,
        leverage=leverage,
        max_leverage=max_leverage,
        reduce_only=reduce_only,
        post_only=post_only,
        time_in_force=tif,
        client_order_id=client_order_id,
        submit_handoff_mode=handoff,
        write_submit_request=write_submit_request,
        reason_codes=reasons or ["MICRO_CANARY_SINGLE_MIN_SIZE_ORDER_REQUEST_VERIFIED"],
    )


def evaluate_hard_caps(settings: Any, order_request: MicroCanaryOrderRequestStatus) -> HardCapsStatus:
    required = _boolish(_setting(settings, "live_real_micro_canary_hard_caps_required", True), True)
    kill_switch = _boolish(_setting(settings, "live_real_micro_canary_kill_switch_armed", True), True)
    single_order_cap = _int(_setting(settings, "live_real_micro_canary_single_order_cap", 1), 1)
    exchange_cap = _int(_setting(settings, "live_real_micro_canary_exchange_submit_cap", 1), 1)
    network_cap = _int(_setting(settings, "live_real_micro_canary_network_submit_cap", 1), 1)
    max_total = _float(_setting(settings, "live_real_micro_canary_max_total_notional_usd", 10.0), 10.0)
    auto_submit_disabled = not _boolish(_setting(settings, "live_real_micro_canary_perform_network_submit", False), False)
    request_count = 1 if order_request.ok else 0
    ok = (
        required
        and kill_switch
        and order_request.ok
        and request_count <= single_order_cap
        and single_order_cap == 1
        and exchange_cap == 1
        and network_cap == 1
        and order_request.notional_usd <= max_total
        and auto_submit_disabled
    )
    reasons: list[str] = []
    if not required:
        reasons.append("MICRO_CANARY_HARD_CAPS_REQUIRED")
    if not kill_switch:
        reasons.append("MICRO_CANARY_KILL_SWITCH_NOT_ARMED")
    if request_count > single_order_cap or single_order_cap != 1:
        reasons.append("MICRO_CANARY_SINGLE_ORDER_CAP_REQUIRED")
    if exchange_cap != 1 or network_cap != 1:
        reasons.append("MICRO_CANARY_EXCHANGE_NETWORK_CAP_MUST_BE_ONE")
    if order_request.notional_usd > max_total:
        reasons.append("MICRO_CANARY_TOTAL_NOTIONAL_CAP_EXCEEDED")
    if not auto_submit_disabled:
        reasons.append("MICRO_CANARY_AUTOMATED_NETWORK_SUBMIT_MUST_REMAIN_DISABLED_IN_PATCH")
    return HardCapsStatus(
        ok=ok,
        required=required,
        kill_switch_armed=kill_switch,
        single_order_cap=single_order_cap,
        exchange_submit_cap=exchange_cap,
        network_submit_cap=network_cap,
        request_count=request_count,
        exchange_submit_count=0,
        network_submit_count=0,
        max_total_notional_usd=max_total,
        requested_notional_usd=order_request.notional_usd,
        automated_network_submit_disabled=auto_submit_disabled,
        reason_codes=reasons or ["MICRO_CANARY_HARD_CAPS_AND_KILL_SWITCH_VERIFIED"],
    )


def build_submit_request_payload(order: MicroCanaryOrderRequestStatus, *, operator_id: str | None) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "request_type": "first_live_real_micro_canary_manual_runtime_handoff_submit_request",
        "created_at_utc": utc_now_iso(),
        "operator_id": operator_id,
        "symbol": order.symbol,
        "side": order.side,
        "order_type": order.order_type,
        "quantity": order.quantity,
        "mark_price_reference": order.mark_price,
        "notional_usd_reference": order.notional_usd,
        "min_notional_usd": order.min_notional_usd,
        "max_notional_usd": order.max_notional_usd,
        "leverage": order.leverage,
        "client_order_id": order.client_order_id,
        "time_in_force": order.time_in_force,
        "reduce_only": order.reduce_only,
        "post_only": order.post_only,
        "submit_handoff_mode": order.submit_handoff_mode,
        "network_submit_performed_by_this_tool": False,
        "requires_external_runtime_submitter": True,
        "risk_warning": "Single live-real micro canary request only; verify exchange/account state immediately before manual runtime submit.",
    }


def build_first_live_real_micro_canary_snapshot(
    settings: Any | None = None,
    source_30w_snapshot: Mapping[str, Any] | None = None,
    *,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_micro_canary_approval: bool = False,
    symbol: str | None = None,
    side: str | None = None,
    quantity: float | str | None = None,
    mark_price: float | str | None = None,
    write_submit_request: bool = False,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_snapshot = dict(_mapping(source_30w_snapshot))
    source = evaluate_source_30w_final_approval(source_snapshot, source_report_path=source_report_path)
    approval = evaluate_micro_canary_approval(
        resolved_settings,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_micro_canary_approval=issue_micro_canary_approval,
    )
    order = evaluate_order_request(
        resolved_settings,
        symbol=symbol,
        side=side,
        quantity=quantity,
        mark_price=mark_price,
        write_submit_request=write_submit_request,
    )
    caps = evaluate_hard_caps(resolved_settings, order)
    no_auto_submit = {
        "ok": caps.automated_network_submit_disabled,
        "network_submit_attempted": False,
        "exchange_submit_performed": False,
        "live_real_order_performed": False,
        "reason_codes": ["MICRO_CANARY_NO_AUTOMATED_NETWORK_SUBMIT_BY_PATCH"],
    }
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not approval.ok:
        reasons.extend(approval.reason_codes)
    if not order.ok:
        reasons.extend(order.reason_codes)
    if not caps.ok:
        reasons.extend(caps.reason_codes)
    if source.ok and approval.ok and order.ok and caps.ok and no_auto_submit["ok"]:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30W_REQUIRED_DECISION
    elif not approval.ok:
        decision = OPERATOR_APPROVAL_REQUIRED_DECISION
    elif not order.ok:
        decision = ORDER_REQUEST_NOT_READY_DECISION
    elif not caps.ok:
        decision = CAPS_NOT_READY_DECISION
    else:
        decision = NOT_READY_DECISION
    ready = decision == READY_DECISION
    submit_request_path: str | None = None
    if ready and write_submit_request:
        request_payload = build_submit_request_payload(order, operator_id=approval.operator_id)
        request_path = Path(reports_dir) / SUBMIT_REQUEST_FILENAME
        write_json_atomic(request_path, request_payload)
        submit_request_path = str(request_path)
    snapshot = FirstLiveRealMicroCanarySnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_30W_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_first_live_real_micro_canary_gate=ready,
        approved_for_first_live_real_micro_canary_submit_request=ready,
        approved_for_manual_runtime_handoff=ready,
        approved_for_exchange_submit=ready,
        approved_for_live_real=ready,
        source_30w_final_operator_approval_verified=source.ok,
        micro_canary_operator_approval_verified=approval.ok,
        single_min_size_order_request_verified=order.ok,
        hard_caps_verified=caps.ok,
        kill_switch_verified=caps.kill_switch_armed,
        automated_network_submit_disabled_verified=bool(no_auto_submit["ok"]),
        submit_request_built=bool(submit_request_path),
        submit_request_path=submit_request_path,
        submit_request_count=1 if ready and write_submit_request else 0,
        order_action_count=0,
        exchange_submit_count=0,
        network_submit_count=0,
        total_notional_usd=order.notional_usd if ready else 0.0,
        max_total_notional_usd=caps.max_total_notional_usd,
        exchange_submit_performed=False,
        network_submit_attempted=False,
        trading_action_performed=False,
        order_actions_performed=False,
        live_real_order_performed=False,
        live_real_order_submitted=False,
        live_real_network_submit_attempted=False,
        runtime_activation_blocked=True,
        training_reload_blocked=True,
        reason_codes=reasons or ["FIRST_LIVE_REAL_MICRO_CANARY_READY_FOR_MANUAL_RUNTIME_HANDOFF_NO_AUTOMATED_NETWORK_SUBMIT"],
        source_30w=source.to_dict(),
        micro_canary_approval=approval.to_dict(),
        order_request=order.to_dict(),
        hard_caps=caps.to_dict(),
        no_automated_network_submit=no_auto_submit,
        source_30w_snapshot=source_snapshot,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    snapshot["approved_for_first_live_real_micro_canary_gate"] = ready
    snapshot["approved_for_first_live_real_micro_canary_submit_request"] = ready
    snapshot["approved_for_manual_runtime_handoff"] = ready
    snapshot["approved_for_exchange_submit"] = ready
    snapshot["approved_for_live_real"] = ready
    return snapshot


def latest_valid_30w_final_operator_approval_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    root = Path(reports_dir)
    candidates = sorted(
        root.glob("4B436630W_live_real_final_operator_approval_*_ready.json"),
        key=lambda item: item.stat().st_mtime if item.exists() else 0.0,
        reverse=True,
    )
    for path in candidates:
        try:
            payload = load_json(path)
        except Exception:
            continue
        if not isinstance(payload, Mapping):
            continue
        status = evaluate_source_30w_final_approval(payload, source_report_path=str(path))
        if status.ok:
            return path, dict(payload)
    return None, {}


def build_from_latest_30w_final_operator_approval_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_micro_canary_approval: bool = False,
    symbol: str | None = None,
    side: str | None = None,
    quantity: float | str | None = None,
    mark_price: float | str | None = None,
    write_submit_request: bool = False,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source = latest_valid_30w_final_operator_approval_report(reports_dir)
    return build_first_live_real_micro_canary_snapshot(
        resolved_settings,
        source,
        source_report_path=str(source_path) if source_path else None,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_micro_canary_approval=issue_micro_canary_approval,
        symbol=symbol,
        side=side,
        quantity=quantity,
        mark_price=mark_price,
        write_submit_request=write_submit_request,
        reports_dir=reports_dir,
    )


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "approval_required" if payload.get("decision") == OPERATOR_APPROVAL_REQUIRED_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, payload)
    approval = _mapping(payload.get("micro_canary_approval"))
    order = _mapping(payload.get("order_request"))
    lines = [
        f"# {CONTRACT_VERSION} First Live-Real Micro Canary",
        "",
        "Consumes 30W final approval and builds one minimum-size live-real micro-canary submit request for manual runtime handoff.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_first_live_real_micro_canary_gate`: `{payload.get('approved_for_first_live_real_micro_canary_gate')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        f"- `source_30w_final_operator_approval_verified`: `{payload.get('source_30w_final_operator_approval_verified')}`",
        f"- `micro_canary_operator_approval_verified`: `{payload.get('micro_canary_operator_approval_verified')}`",
        f"- `single_min_size_order_request_verified`: `{payload.get('single_min_size_order_request_verified')}`",
        f"- `hard_caps_verified`: `{payload.get('hard_caps_verified')}`",
        f"- `kill_switch_verified`: `{payload.get('kill_switch_verified')}`",
        f"- `automated_network_submit_disabled_verified`: `{payload.get('automated_network_submit_disabled_verified')}`",
        f"- `submit_request_built`: `{payload.get('submit_request_built')}`",
        f"- `submit_request_path`: `{payload.get('submit_request_path')}`",
        f"- `exchange_submit_performed`: `{payload.get('exchange_submit_performed')}`",
        f"- `network_submit_attempted`: `{payload.get('network_submit_attempted')}`",
        f"- `live_real_order_performed`: `{payload.get('live_real_order_performed')}`",
        "",
        "## Operator approval",
        f"- `operator_id`: `{approval.get('operator_id')}`",
        f"- `approval_token_matched`: `{approval.get('approval_token_matched')}`",
        f"- `captured_at_utc`: `{approval.get('captured_at_utc')}`",
        "",
        "## Order request",
        f"- `symbol`: `{order.get('symbol')}`",
        f"- `side`: `{order.get('side')}`",
        f"- `quantity`: `{order.get('quantity')}`",
        f"- `mark_price`: `{order.get('mark_price')}`",
        f"- `notional_usd`: `{order.get('notional_usd')}`",
        f"- `submit_handoff_mode`: `{order.get('submit_handoff_mode')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
