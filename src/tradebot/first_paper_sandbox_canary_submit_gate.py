from __future__ import annotations

import json
import math
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30Q"
SOURCE_30P_CONTRACT_VERSION = "4B.4.3.6.6.30P"
SOURCE_30P_READY_DECISION = "PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL"
REPORT_TYPE = "first_paper_sandbox_canary_submit_gate_order_intent_submit_guarded_no_live_real"
REPORT_PREFIX = "4B436630Q_first_paper_sandbox_canary_submit_gate"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
CANARY_ORDER_INTENT_DEFAULT_NAME = "4B436630Q_single_canary_order_intent.json"

READY_DECISION = "FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_READY_ORDER_INTENT_BUILT_SUBMIT_GUARDED_NO_LIVE_REAL"
SOURCE_30P_REQUIRED_DECISION = "FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_30P_SUBMIT_ARM_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
APPROVAL_REQUIRED_DECISION = "FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_OPERATOR_APPROVAL_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

APPROVAL_PHRASE = "APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_live_order_blocked": True,
    "paper_order_enablement_still_blocked": True,
    "exchange_submit_path_guarded": True,
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
    "network_submit_attempted": False,
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30PSubmitArmStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    submit_arm_preflight_ready: bool
    sandbox_api_mode_ok: bool
    endpoint_ok: bool
    min_notional_ok: bool
    lot_size_ok: bool
    risk_caps_ok: bool
    kill_switch_ok: bool
    approved_for_paper_candidate: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    submit_still_blocked: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanaryApprovalStatus:
    ok: bool
    required: bool
    operator_id: str
    approval_phrase: str
    approval_token_matches_phrase: bool
    approval_issued: bool
    approval_issued_at_ms: int
    approval_ttl_sec: int
    approval_expires_at_ms: int
    approval_expired: bool
    canary_operator_approval_verified: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanaryReadinessStatus:
    ok: bool
    api_mode_ok: bool
    endpoint_ok: bool
    min_notional_ok: bool
    lot_size_ok: bool
    risk_caps_ok: bool
    kill_switch_ok: bool
    execution_mode: str
    runtime_envelope: str
    market_type: str
    base_url: str
    symbol: str
    side: str
    order_type: str
    quote_notional_usd: float
    canary_notional_cap_usd: float
    min_notional_usd: float
    estimated_price_usd: float
    raw_qty: float
    rounded_qty: float
    min_qty: float
    step_size: float
    max_daily_trades_cap: int
    max_daily_loss_usd: float
    max_open_orders: int
    kill_switch_enabled: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanaryOrderIntentStatus:
    ok: bool
    required: bool
    intent_built: bool
    intent_written: bool
    intent_path: str
    intent: dict[str, Any]
    network_submit_allowed: bool
    submit_path_guarded: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SubmitGuardStatus:
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
    exchange_submit_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FirstCanarySubmitGateDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_first_paper_sandbox_canary_submit_gate: bool
    approved_for_30p_submit_arm_consumption: bool
    approved_for_operator_canary_approval: bool
    approved_for_single_sandbox_order_intent: bool
    approved_for_sandbox_submit_path_armed_candidate: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    source_30p_submit_arm_verified: bool
    operator_canary_approval_verified: bool
    sandbox_submit_readiness_verified: bool
    single_sandbox_order_intent_built: bool
    canary_order_intent_written: bool
    exchange_submit_path_guarded: bool
    no_live_real_verified: bool
    submit_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    order_actions_performed: bool
    exchange_submit_performed: bool
    reason_codes: list[str]
    source_30p: dict[str, Any]
    operator_canary_approval: dict[str, Any]
    sandbox_submit_readiness: dict[str, Any]
    single_sandbox_order_intent: dict[str, Any]
    submit_guard: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30p_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_ms() -> int:
    return int(time.time() * 1000)


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


def latest_valid_30p_submit_arm_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    reports = Path(reports_dir)
    matches = sorted(
        [item for item in reports.glob("4B436630P_paper_sandbox_submit_arm_preflight_*_ready.json") if item.is_file()],
        key=lambda item: item.name,
        reverse=True,
    )
    for item in matches:
        try:
            payload = load_json(item)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and evaluate_source_30p_submit_arm(payload, source_report_path=str(item)).ok:
            return item, payload
    return None, {}


def default_order_intent_path(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path:
    return Path(reports_dir) / CANARY_ORDER_INTENT_DEFAULT_NAME


def _nested_checks(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for key in ("checks", "source_30p", "submit_arm", "sandbox_submit_arm_preflight", "module_probe", "risk_controls"):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            checks.update(value)
    return checks


def evaluate_source_30p_submit_arm(source_30p_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30PSubmitArmStatus:
    checks = _nested_checks(source_30p_snapshot)
    contract = str(source_30p_snapshot.get("contract_version") or "") or None
    decision = str(source_30p_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30P_READY_DECISION
    ready_flag = _boolish(_first_present(source_30p_snapshot, (
        "approved_for_paper_sandbox_submit_arm_preflight",
        "approved_for_submit_arm_preflight",
        "approved_for_paper_sandbox_submit_arm",
        "submit_arm_preflight_ready",
    ), decision_ok), decision_ok)
    api_mode_ok = _boolish(_first_present(source_30p_snapshot, ("api_mode_ok", "sandbox_api_mode_ok"), checks.get("api_mode_check") or checks.get("api_mode_ok")), decision_ok)
    endpoint_ok = _boolish(_first_present(source_30p_snapshot, ("endpoint_ok", "sandbox_endpoint_ok"), checks.get("endpoint_check") or checks.get("endpoint_ok")), decision_ok)
    min_notional_ok = _boolish(_first_present(source_30p_snapshot, ("min_notional_ok", "minNotional_ok"), checks.get("min_notional_check") or checks.get("min_notional_ok")), decision_ok)
    lot_size_ok = _boolish(_first_present(source_30p_snapshot, ("lot_size_ok", "lotSize_ok"), checks.get("lot_size_check") or checks.get("lot_size_ok")), decision_ok)
    risk_caps_ok = _boolish(_first_present(source_30p_snapshot, ("risk_caps_ok", "caps_ok"), checks.get("risk_caps_check") or checks.get("risk_caps_ok")), decision_ok)
    kill_switch_ok = _boolish(_first_present(source_30p_snapshot, ("kill_switch_ok", "kill_switch_check_ok"), checks.get("kill_switch_check") or checks.get("kill_switch_ok")), decision_ok)
    paper_candidate = _boolish(source_30p_snapshot.get("approved_for_paper_candidate"), True if decision_ok else False)
    approved_exchange = _boolish(source_30p_snapshot.get("approved_for_exchange_submit"), False)
    approved_live = _boolish(source_30p_snapshot.get("approved_for_live_real"), False)
    exchange_performed = _boolish(source_30p_snapshot.get("exchange_submit_performed"), False)
    trading_action = _boolish(source_30p_snapshot.get("trading_action_performed"), False)
    order_actions = _boolish(source_30p_snapshot.get("order_actions_performed"), False)
    submit_blocked = _boolish(_first_present(source_30p_snapshot, ("submit_still_blocked", "submit_blocked", "exchange_submit_still_blocked"), True), True) and not approved_exchange and not exchange_performed
    reasons: list[str] = []
    if contract not in {SOURCE_30P_CONTRACT_VERSION, "4B.4.3.6.6.30P-H3"}:
        reasons.append("SOURCE_30P_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30P_READY_SUBMIT_ARM_DECISION_REQUIRED")
    if not ready_flag:
        reasons.append("SOURCE_30P_SUBMIT_ARM_PREFLIGHT_NOT_READY")
    if not api_mode_ok:
        reasons.append("SOURCE_30P_API_MODE_NOT_VERIFIED")
    if not endpoint_ok:
        reasons.append("SOURCE_30P_ENDPOINT_NOT_VERIFIED")
    if not min_notional_ok:
        reasons.append("SOURCE_30P_MIN_NOTIONAL_NOT_VERIFIED")
    if not lot_size_ok:
        reasons.append("SOURCE_30P_LOT_SIZE_NOT_VERIFIED")
    if not risk_caps_ok:
        reasons.append("SOURCE_30P_RISK_CAPS_NOT_VERIFIED")
    if not kill_switch_ok:
        reasons.append("SOURCE_30P_KILL_SWITCH_NOT_VERIFIED")
    if not paper_candidate:
        reasons.append("SOURCE_30P_PAPER_CANDIDATE_NOT_PRESERVED")
    if approved_exchange or exchange_performed:
        reasons.append("SOURCE_30P_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if approved_live:
        reasons.append("SOURCE_30P_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30P_ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    if not submit_blocked:
        reasons.append("SOURCE_30P_SUBMIT_NOT_BLOCKED")
    return Source30PSubmitArmStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        submit_arm_preflight_ready=ready_flag,
        sandbox_api_mode_ok=api_mode_ok,
        endpoint_ok=endpoint_ok,
        min_notional_ok=min_notional_ok,
        lot_size_ok=lot_size_ok,
        risk_caps_ok=risk_caps_ok,
        kill_switch_ok=kill_switch_ok,
        approved_for_paper_candidate=paper_candidate,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        submit_still_blocked=submit_blocked,
        exchange_submit_performed=exchange_performed,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30P_SUBMIT_ARM_PREFLIGHT_VERIFIED"],
    )


def evaluate_canary_approval(
    settings: Any,
    *,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_canary_approval: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> CanaryApprovalStatus:
    required = _boolish(_setting(settings, "first_paper_sandbox_canary_operator_approval_required", True), True)
    phrase = str(_setting(settings, "first_paper_sandbox_canary_operator_approval_phrase", APPROVAL_PHRASE) or APPROVAL_PHRASE)
    resolved_operator = str(operator_id if operator_id is not None else _setting(settings, "first_paper_sandbox_canary_operator_id", "") or "").strip()
    resolved_token = str(approval_token if approval_token is not None else _setting(settings, "first_paper_sandbox_canary_operator_approval_token", "") or "").strip()
    resolved_ttl = int(ttl_sec if ttl_sec is not None else _setting(settings, "first_paper_sandbox_canary_operator_approval_ttl_sec", 900) or 900)
    current_ms = int(now_ms if now_ms is not None else _now_ms())
    configured_issued = _boolish(_setting(settings, "first_paper_sandbox_canary_operator_approval_issued", False), False)
    issued = bool(issue_canary_approval or configured_issued)
    issued_at = int(current_ms if issue_canary_approval else _setting(settings, "first_paper_sandbox_canary_operator_approval_issued_at_ms", 0) or 0)
    expires_at = issued_at + max(resolved_ttl, 0) * 1000 if issued_at > 0 else 0
    expired = bool(issued and expires_at > 0 and current_ms > expires_at)
    token_ok = resolved_token == phrase
    reasons: list[str] = []
    if not required:
        reasons.append("CANARY_OPERATOR_APPROVAL_MUST_REMAIN_REQUIRED")
    if not resolved_operator:
        reasons.append("CANARY_OPERATOR_ID_REQUIRED")
    if not issued:
        reasons.append("CANARY_OPERATOR_APPROVAL_NOT_ISSUED")
    if not token_ok:
        reasons.append("CANARY_OPERATOR_APPROVAL_TOKEN_MISMATCH")
    if resolved_ttl <= 0:
        reasons.append("CANARY_OPERATOR_APPROVAL_TTL_INVALID")
    if expired:
        reasons.append("CANARY_OPERATOR_APPROVAL_EXPIRED")
    ok = required and bool(resolved_operator) and issued and token_ok and resolved_ttl > 0 and not expired
    return CanaryApprovalStatus(
        ok=ok,
        required=required,
        operator_id=resolved_operator,
        approval_phrase=phrase,
        approval_token_matches_phrase=token_ok,
        approval_issued=issued,
        approval_issued_at_ms=issued_at,
        approval_ttl_sec=resolved_ttl,
        approval_expires_at_ms=expires_at,
        approval_expired=expired,
        canary_operator_approval_verified=ok,
        reason_codes=reasons or ["FIRST_PAPER_SANDBOX_CANARY_OPERATOR_APPROVAL_VERIFIED"],
    )


def _runtime_envelope(settings: Any) -> str:
    return str(_setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "sandbox_only").lower()


def _execution_mode(settings: Any) -> str:
    return str(_setting(settings, "execution_mode", "dry_run") or "dry_run").lower()


def _market_type(settings: Any) -> str:
    return str(_setting(settings, "market_type", "spot_demo") or "spot_demo").lower()


def _base_url(settings: Any) -> str:
    return str(_setting(settings, "base_url", "") or "").lower()


def _round_down_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    return math.floor((value + 1e-12) / step) * step


def evaluate_canary_readiness(settings: Any, source_30p_snapshot: Mapping[str, Any]) -> CanaryReadinessStatus:
    execution_mode = _execution_mode(settings)
    runtime_envelope = _runtime_envelope(settings)
    market_type = _market_type(settings)
    base_url = _base_url(settings)
    symbol = str(_setting(settings, "symbol", "ETHUSDT") or "ETHUSDT").upper()
    side = str(_setting(settings, "first_paper_sandbox_canary_side", "BUY") or "BUY").upper()
    order_type = str(_setting(settings, "first_paper_sandbox_canary_order_type", "MARKET") or "MARKET").upper()
    min_notional = _float(_setting(settings, "first_paper_sandbox_canary_min_notional_usd", 5.0), 5.0)
    canary_cap = _float(_setting(settings, "first_paper_sandbox_canary_notional_cap_usd", 10.0), 10.0)
    quote_notional = _float(_setting(settings, "first_paper_sandbox_canary_quote_notional_usd", 10.0), 10.0)
    estimated_price = _float(_setting(settings, "first_paper_sandbox_canary_estimated_price_usd", 2500.0), 2500.0)
    min_qty = _float(_setting(settings, "first_paper_sandbox_canary_min_qty", 0.0001), 0.0001)
    step_size = _float(_setting(settings, "first_paper_sandbox_canary_step_size", 0.0001), 0.0001)
    max_daily_trades = _int(_setting(settings, "paper_max_daily_trades_cap", 5), 5)
    max_daily_loss = _float(_setting(settings, "paper_max_daily_loss_usd", 5.0), 5.0)
    max_open_orders = _int(_setting(settings, "paper_transition_max_open_orders", 1), 1)
    kill_switch = _boolish(_setting(settings, "paper_kill_switch_enabled", True), True)
    raw_qty = quote_notional / estimated_price if estimated_price > 0 else 0.0
    rounded_qty = _round_down_step(raw_qty, step_size)
    api_mode_ok = execution_mode == "dry_run" and runtime_envelope == "sandbox_only" and market_type in {"spot_demo", "spot_testnet"}
    endpoint_ok = execution_mode == "dry_run" or "demo" in base_url or "testnet" in base_url
    min_notional_ok = quote_notional >= min_notional > 0
    lot_size_ok = rounded_qty >= min_qty > 0 and step_size > 0
    risk_caps_ok = 0 < quote_notional <= canary_cap and max_daily_trades > 0 and max_daily_loss > 0 and max_open_orders > 0
    kill_switch_ok = kill_switch
    reasons: list[str] = []
    if not api_mode_ok:
        reasons.append("CANARY_API_MODE_NOT_SANDBOX_DRY_RUN")
    if not endpoint_ok:
        reasons.append("CANARY_ENDPOINT_NOT_SANDBOX_OR_DRY_RUN")
    if not min_notional_ok:
        reasons.append("CANARY_MIN_NOTIONAL_CHECK_FAILED")
    if not lot_size_ok:
        reasons.append("CANARY_LOT_SIZE_CHECK_FAILED")
    if not risk_caps_ok:
        reasons.append("CANARY_RISK_CAPS_CHECK_FAILED")
    if not kill_switch_ok:
        reasons.append("CANARY_KILL_SWITCH_CHECK_FAILED")
    return CanaryReadinessStatus(
        ok=api_mode_ok and endpoint_ok and min_notional_ok and lot_size_ok and risk_caps_ok and kill_switch_ok,
        api_mode_ok=api_mode_ok,
        endpoint_ok=endpoint_ok,
        min_notional_ok=min_notional_ok,
        lot_size_ok=lot_size_ok,
        risk_caps_ok=risk_caps_ok,
        kill_switch_ok=kill_switch_ok,
        execution_mode=execution_mode,
        runtime_envelope=runtime_envelope,
        market_type=market_type,
        base_url=base_url,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quote_notional_usd=quote_notional,
        canary_notional_cap_usd=canary_cap,
        min_notional_usd=min_notional,
        estimated_price_usd=estimated_price,
        raw_qty=raw_qty,
        rounded_qty=rounded_qty,
        min_qty=min_qty,
        step_size=step_size,
        max_daily_trades_cap=max_daily_trades,
        max_daily_loss_usd=max_daily_loss,
        max_open_orders=max_open_orders,
        kill_switch_enabled=kill_switch,
        reason_codes=reasons or ["SANDBOX_CANARY_SUBMIT_READINESS_VERIFIED"],
    )


def evaluate_submit_guard(settings: Any, source_30p_snapshot: Mapping[str, Any]) -> SubmitGuardStatus:
    required = _boolish(_setting(settings, "first_paper_sandbox_canary_submit_guard_required", True), True)
    approved = _boolish(source_30p_snapshot.get("approved_for_exchange_submit"), False)
    exchange_performed = _boolish(source_30p_snapshot.get("exchange_submit_performed"), False)
    network_attempted = _boolish(source_30p_snapshot.get("network_submit_attempted"), False)
    exchange_order_id_present = bool(source_30p_snapshot.get("exchange_order_id")) or _boolish(source_30p_snapshot.get("exchange_order_id_present"), False)
    exchange_client_order_id_present = bool(source_30p_snapshot.get("exchange_client_order_id")) or _boolish(source_30p_snapshot.get("exchange_client_order_id_present"), False)
    reasons: list[str] = []
    if not required:
        reasons.append("CANARY_SUBMIT_GUARD_MUST_REMAIN_REQUIRED")
    if approved or exchange_performed or network_attempted:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if exchange_order_id_present:
        reasons.append("EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if exchange_client_order_id_present:
        reasons.append("EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return SubmitGuardStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        exchange_order_id_present=exchange_order_id_present,
        exchange_client_order_id_present=exchange_client_order_id_present,
        reason_codes=reasons or ["EXCHANGE_SUBMIT_PATH_GUARDED_CANARY_INTENT_ONLY"],
    )


def evaluate_no_live_real(settings: Any, source_30p_snapshot: Mapping[str, Any]) -> NoLiveRealStatus:
    required = _boolish(_setting(settings, "first_paper_sandbox_canary_no_live_real_required", True), True)
    approved_live = _boolish(source_30p_snapshot.get("approved_for_live_real"), False)
    live_armed = _boolish(_setting(settings, "live_trading_armed", False), False)
    live_confirm = _boolish(_setting(settings, "live_real_double_confirm", False), False)
    exchange_performed = _boolish(source_30p_snapshot.get("exchange_submit_performed"), False)
    reasons: list[str] = []
    if not required:
        reasons.append("CANARY_NO_LIVE_REAL_MUST_REMAIN_REQUIRED")
    if approved_live or live_armed or live_confirm:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_ENABLED_OR_ARMED")
    if exchange_performed:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_PERFORMED")
    return NoLiveRealStatus(
        ok=required and not reasons,
        required=required,
        approved_for_live_real=approved_live,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_confirm,
        exchange_submit_performed=exchange_performed,
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_FIRST_CANARY_GATE"],
    )


def build_canary_order_intent(
    readiness: CanaryReadinessStatus,
    source_30p_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    current_ms = int(now_ms if now_ms is not None else _now_ms())
    return {
        "intent_id": f"canary-intent-4B436630Q-{current_ms}",
        "contract_version": CONTRACT_VERSION,
        "event_type": "first_paper_sandbox_canary_single_order_intent_submit_guarded_no_exchange_submit",
        "generated_at_utc": utc_now_iso(),
        "source_30p_report_path": source_report_path,
        "source_30p_decision": source_30p_snapshot.get("decision"),
        "symbol": readiness.symbol,
        "side": readiness.side,
        "order_type": readiness.order_type,
        "quote_notional_usd": readiness.quote_notional_usd,
        "quantity": readiness.rounded_qty,
        "estimated_price_usd": readiness.estimated_price_usd,
        "min_notional_usd": readiness.min_notional_usd,
        "min_qty": readiness.min_qty,
        "step_size": readiness.step_size,
        "runtime_envelope": readiness.runtime_envelope,
        "execution_mode": readiness.execution_mode,
        "market_type": readiness.market_type,
        "base_url": readiness.base_url,
        "operator_approved_canary_gate": True,
        "sandbox_submit_path_armed_candidate": True,
        "submit_path_guarded": True,
        "submit_to_exchange": False,
        "submitted_to_exchange": False,
        "network_submit_attempted": False,
        "exchange_submit_performed": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
    }


def evaluate_canary_order_intent(
    settings: Any,
    source_30p_snapshot: Mapping[str, Any],
    readiness: CanaryReadinessStatus,
    *,
    source_report_path: str | None,
    intent_path: str | os.PathLike[str],
    build_allowed: bool,
    write_intent: bool = False,
    now_ms: int | None = None,
) -> CanaryOrderIntentStatus:
    required = _boolish(_setting(settings, "first_paper_sandbox_canary_order_intent_required", True), True)
    intent = build_canary_order_intent(readiness, source_30p_snapshot, source_report_path=source_report_path, now_ms=now_ms)
    reasons: list[str] = []
    if not required:
        reasons.append("CANARY_ORDER_INTENT_MUST_REMAIN_REQUIRED")
    if not readiness.ok:
        reasons.append("CANARY_READINESS_NOT_VERIFIED")
    if bool(intent.get("submit_to_exchange")) or bool(intent.get("submitted_to_exchange")) or bool(intent.get("network_submit_attempted")) or bool(intent.get("exchange_submit_performed")):
        reasons.append("CANARY_INTENT_UNEXPECTED_EXCHANGE_SUBMIT")
    intent_built = required and build_allowed and not reasons
    intent_written = False
    if intent_built and write_intent:
        write_json_atomic(intent_path, intent)
        intent_written = True
    return CanaryOrderIntentStatus(
        ok=intent_built,
        required=required,
        intent_built=intent_built,
        intent_written=intent_written,
        intent_path=Path(intent_path).as_posix(),
        intent=intent if intent_built else {},
        network_submit_allowed=False,
        submit_path_guarded=True,
        reason_codes=reasons or ["SINGLE_SANDBOX_CANARY_ORDER_INTENT_BUILT_SUBMIT_GUARDED"],
    )


def build_first_paper_sandbox_canary_submit_gate_snapshot(
    settings: Any,
    source_30p_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_canary_approval: bool = False,
    ttl_sec: int | None = None,
    intent_path: str | os.PathLike[str] | None = None,
    write_intent: bool = False,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30p_submit_arm(source_30p_snapshot, source_report_path=source_report_path)
    approval = evaluate_canary_approval(
        settings,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_canary_approval=issue_canary_approval,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )
    readiness = evaluate_canary_readiness(settings, source_30p_snapshot)
    submit_guard = evaluate_submit_guard(settings, source_30p_snapshot)
    no_live = evaluate_no_live_real(settings, source_30p_snapshot)
    resolved_intent_path = Path(intent_path) if intent_path is not None else Path(str(_setting(settings, "first_paper_sandbox_canary_order_intent_path", "") or "") or default_order_intent_path(DEFAULT_REPORTS_DIR))
    intent = evaluate_canary_order_intent(
        settings,
        source_30p_snapshot,
        readiness,
        source_report_path=source_report_path,
        intent_path=resolved_intent_path,
        build_allowed=source.ok and approval.ok and readiness.ok and submit_guard.ok and no_live.ok,
        write_intent=write_intent,
        now_ms=now_ms,
    )
    reasons = [*source.reason_codes, *approval.reason_codes, *readiness.reason_codes, *intent.reason_codes, *submit_guard.reason_codes, *no_live.reason_codes]
    reasons.extend(["SINGLE_SANDBOX_CANARY_ORDER_INTENT_ONLY", "EXCHANGE_SUBMIT_PATH_STILL_GUARDED", "NO_LIVE_REAL_VERIFIED"])
    ready = source.ok and approval.ok and readiness.ok and intent.ok and submit_guard.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30P_REQUIRED_DECISION
    elif not approval.ok:
        decision = APPROVAL_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = FirstCanarySubmitGateDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_first_paper_sandbox_canary_submit_gate=ready,
        approved_for_30p_submit_arm_consumption=source.ok,
        approved_for_operator_canary_approval=approval.ok,
        approved_for_single_sandbox_order_intent=intent.intent_built,
        approved_for_sandbox_submit_path_armed_candidate=ready,
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        source_30p_submit_arm_verified=source.ok,
        operator_canary_approval_verified=approval.ok,
        sandbox_submit_readiness_verified=readiness.ok,
        single_sandbox_order_intent_built=intent.intent_built,
        canary_order_intent_written=intent.intent_written,
        exchange_submit_path_guarded=submit_guard.ok and intent.submit_path_guarded,
        no_live_real_verified=no_live.ok,
        submit_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        order_actions_performed=False,
        exchange_submit_performed=False,
        reason_codes=reasons,
        source_30p=source.to_dict(),
        operator_canary_approval=approval.to_dict(),
        sandbox_submit_readiness=readiness.to_dict(),
        single_sandbox_order_intent=intent.to_dict(),
        submit_guard=submit_guard.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30p_snapshot=dict(source_30p_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30p_submit_arm_gate": True,
        "explicit_operator_canary_approval_gate": True,
        "sandbox_submit_readiness_gate": True,
        "api_mode_gate": readiness.api_mode_ok,
        "endpoint_gate": readiness.endpoint_ok,
        "min_notional_gate": readiness.min_notional_ok,
        "lot_size_gate": readiness.lot_size_ok,
        "risk_caps_gate": readiness.risk_caps_ok,
        "kill_switch_gate": readiness.kill_switch_ok,
        "single_sandbox_demo_order_intent_gate": intent.intent_built,
        "exchange_submit_guard_gate": submit_guard.ok,
        "no_live_real_gate": no_live.ok,
    })
    return payload


def build_from_latest_30p_ready_report(
    settings: Any | None = None,
    *,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_canary_approval: bool = False,
    ttl_sec: int | None = None,
    intent_path: str | os.PathLike[str] | None = None,
    write_intent: bool = False,
    now_ms: int | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source_snapshot = latest_valid_30p_submit_arm_report(reports_dir)
    resolved_intent_path = intent_path
    if resolved_intent_path is None:
        configured = str(_setting(resolved_settings, "first_paper_sandbox_canary_order_intent_path", "") or "").strip()
        resolved_intent_path = Path(configured) if configured else default_order_intent_path(reports_dir)
    return build_first_paper_sandbox_canary_submit_gate_snapshot(
        resolved_settings,
        source_snapshot,
        source_report_path=str(source_path) if source_path else None,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_canary_approval=issue_canary_approval,
        ttl_sec=ttl_sec,
        intent_path=resolved_intent_path,
        write_intent=write_intent,
        now_ms=now_ms,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "")
    if decision == READY_DECISION:
        return "ready"
    if decision == APPROVAL_REQUIRED_DECISION:
        return "approval_required"
    if decision == SOURCE_30P_REQUIRED_DECISION:
        return "30p_required"
    return "not_ready"


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    suffix = _decision_suffix(payload)
    stamp = utc_stamp()
    json_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, payload)
    lines = [
        f"# {CONTRACT_VERSION} First Paper Sandbox Canary Submit Gate",
        "",
        "This report consumes the 30P-H3 submit-arm preflight, verifies explicit operator canary approval, builds one sandbox/demo order intent, and keeps the exchange submit path guarded with no live-real.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_first_paper_sandbox_canary_submit_gate`: `{payload.get('approved_for_first_paper_sandbox_canary_submit_gate')}`",
        f"- `approved_for_30p_submit_arm_consumption`: `{payload.get('approved_for_30p_submit_arm_consumption')}`",
        f"- `approved_for_operator_canary_approval`: `{payload.get('approved_for_operator_canary_approval')}`",
        f"- `approved_for_single_sandbox_order_intent`: `{payload.get('approved_for_single_sandbox_order_intent')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        f"- `submit_still_blocked`: `{payload.get('submit_still_blocked')}`",
        f"- `exchange_submit_performed`: `{payload.get('exchange_submit_performed')}`",
        f"- `trading_action_performed`: `{payload.get('trading_action_performed')}`",
        "",
        "## Gate checks",
        f"- `api_mode_gate`: `{payload.get('api_mode_gate')}`",
        f"- `endpoint_gate`: `{payload.get('endpoint_gate')}`",
        f"- `min_notional_gate`: `{payload.get('min_notional_gate')}`",
        f"- `lot_size_gate`: `{payload.get('lot_size_gate')}`",
        f"- `risk_caps_gate`: `{payload.get('risk_caps_gate')}`",
        f"- `kill_switch_gate`: `{payload.get('kill_switch_gate')}`",
        f"- `exchange_submit_guard_gate`: `{payload.get('exchange_submit_guard_gate')}`",
        f"- `no_live_real_gate`: `{payload.get('no_live_real_gate')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return json_path, md_path
