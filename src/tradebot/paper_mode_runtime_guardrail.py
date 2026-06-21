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

CONTRACT_VERSION = "4B.4.3.6.6.30S"
SOURCE_30R_CONTRACT_VERSION = "4B.4.3.6.6.30R"
SOURCE_30R_READY_DECISION = "PAPER_SANDBOX_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_SUBMIT_GUARDED_NO_LIVE_REAL"
REPORT_TYPE = "paper_mode_runtime_guardrail_loop_caps_kill_switch_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630S_paper_mode_runtime_guardrail"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_MODE_RUNTIME_GUARDRAIL_READY_GUARDED_LOOP_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOURCE_30R_REQUIRED_DECISION = "PAPER_MODE_RUNTIME_GUARDRAIL_30R_RECONCILIATION_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
LOOP_NOT_READY_DECISION = "PAPER_MODE_RUNTIME_GUARDRAIL_LOOP_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
CAPS_NOT_READY_DECISION = "PAPER_MODE_RUNTIME_GUARDRAIL_STRICT_CAPS_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
KILL_SWITCH_REQUIRED_DECISION = "PAPER_MODE_RUNTIME_GUARDRAIL_KILL_SWITCH_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_MODE_RUNTIME_GUARDRAIL_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

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
class Source30RReconciliationStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    reconciliation_ready: bool
    source_30q_consumed: bool
    canary_order_intent_consumed: bool
    intent_fill_account_reconciled: bool
    submit_remained_guarded_verified: bool
    mismatch_zero_verified: bool
    mismatch_count: int
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    trading_action_performed: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GuardedRuntimeTick:
    index: int
    event_type: str
    signal: str
    action: str
    order_action_performed: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    notional_usd: float
    reason_code: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GuardedRuntimeLoopStatus:
    ok: bool
    required: bool
    requested_ticks: int
    executed_ticks: int
    tick_cap: int
    loop_completed: bool
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    trading_action_count: int
    total_notional_usd: float
    ticks: list[dict[str, Any]]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StrictCapsStatus:
    ok: bool
    required: bool
    tick_cap: int
    executed_ticks: int
    order_action_cap: int
    observed_order_actions: int
    exchange_submit_cap: int
    observed_exchange_submits: int
    network_submit_cap: int
    observed_network_submits: int
    max_notional_usd: float
    observed_notional_usd: float
    runtime_seconds_cap: int
    observed_runtime_seconds: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class KillSwitchProofStatus:
    ok: bool
    required: bool
    kill_switch_enabled: bool
    paper_order_enablement_still_blocked: bool
    runtime_activation_blocked: bool
    order_action_cap_zero: bool
    exchange_submit_cap_zero: bool
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
    order_actions_performed: bool
    trading_action_performed: bool
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
class PaperModeRuntimeGuardrailDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_mode_runtime_guardrail: bool
    approved_for_30r_reconciliation_consumption: bool
    approved_for_guarded_runtime_loop: bool
    approved_for_strict_caps: bool
    approved_for_kill_switch_proof: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    source_30r_reconciliation_verified: bool
    guarded_runtime_loop_verified: bool
    strict_caps_verified: bool
    kill_switch_verified: bool
    no_exchange_submit_verified: bool
    no_live_real_verified: bool
    loop_tick_count: int
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    mismatch_count: int
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    order_actions_performed: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    reason_codes: list[str]
    source_30r: dict[str, Any]
    guarded_runtime_loop: dict[str, Any]
    strict_caps: dict[str, Any]
    kill_switch_proof: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30r_snapshot: dict[str, Any]

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
        "source_30r",
        "paper_sandbox_canary_reconciliation",
        "intent_fill_account_reconciliation",
        "submit_guard_proof",
        "no_live_real",
    ):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def evaluate_source_30r_reconciliation(source_30r_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30RReconciliationStatus:
    nested = _nested(source_30r_snapshot)
    contract = str(source_30r_snapshot.get("contract_version") or "") or None
    decision = str(source_30r_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30R_READY_DECISION
    ready = _boolish(_first_present(source_30r_snapshot, ("approved_for_paper_sandbox_canary_reconciliation", "reconciliation_ready"), nested.get("approved_for_paper_sandbox_canary_reconciliation", decision_ok)), decision_ok)
    source_30q = _boolish(_first_present(source_30r_snapshot, ("source_30q_canary_gate_verified", "approved_for_30q_canary_intent_consumption"), nested.get("source_30q_canary_gate_verified", decision_ok)), decision_ok)
    intent_consumed = _boolish(_first_present(source_30r_snapshot, ("canary_order_intent_consumed",), nested.get("canary_order_intent_consumed", decision_ok)), decision_ok)
    reconciled = _boolish(_first_present(source_30r_snapshot, ("intent_fill_account_reconciled",), nested.get("intent_fill_account_reconciled", decision_ok)), decision_ok)
    submit_guarded = _boolish(_first_present(source_30r_snapshot, ("submit_remained_guarded_verified",), nested.get("submit_remained_guarded_verified", True)), True)
    mismatch_count = _int(_first_present(source_30r_snapshot, ("mismatch_count",), nested.get("mismatch_count", 0)), 0)
    mismatch_zero = _boolish(_first_present(source_30r_snapshot, ("mismatch_zero_verified", "approved_for_mismatch_zero_proof"), nested.get("mismatch_zero_verified", mismatch_count == 0)), mismatch_count == 0)
    approved_exchange = _boolish(source_30r_snapshot.get("approved_for_exchange_submit"), False)
    approved_live = _boolish(source_30r_snapshot.get("approved_for_live_real"), False)
    exchange_performed = _boolish(source_30r_snapshot.get("exchange_submit_performed"), False)
    network_attempted = _boolish(source_30r_snapshot.get("network_submit_attempted"), False)
    trading_action = _boolish(source_30r_snapshot.get("trading_action_performed"), False)
    order_actions = _boolish(source_30r_snapshot.get("order_actions_performed"), False)
    reasons: list[str] = []
    if contract != SOURCE_30R_CONTRACT_VERSION:
        reasons.append("SOURCE_30R_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30R_READY_RECONCILIATION_DECISION_REQUIRED")
    if not ready:
        reasons.append("SOURCE_30R_RECONCILIATION_NOT_READY")
    if not source_30q or not intent_consumed or not reconciled:
        reasons.append("SOURCE_30R_RECONCILIATION_COMPONENTS_NOT_VERIFIED")
    if not submit_guarded:
        reasons.append("SOURCE_30R_SUBMIT_GUARD_NOT_VERIFIED")
    if not mismatch_zero or mismatch_count != 0:
        reasons.append("SOURCE_30R_MISMATCH_ZERO_REQUIRED")
    if approved_exchange or exchange_performed or network_attempted:
        reasons.append("SOURCE_30R_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if approved_live:
        reasons.append("SOURCE_30R_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30R_TRADING_OR_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30RReconciliationStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        reconciliation_ready=ready,
        source_30q_consumed=source_30q,
        canary_order_intent_consumed=intent_consumed,
        intent_fill_account_reconciled=reconciled,
        submit_remained_guarded_verified=submit_guarded,
        mismatch_zero_verified=mismatch_zero,
        mismatch_count=mismatch_count,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30R_RECONCILIATION_VERIFIED"],
    )


def latest_valid_30r_reconciliation_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    reports = Path(reports_dir)
    matches = sorted(
        [item for item in reports.glob("4B436630R_paper_sandbox_canary_reconciliation_*_ready.json") if item.is_file()],
        key=lambda item: item.name,
        reverse=True,
    )
    for item in matches:
        try:
            payload = load_json(item)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and evaluate_source_30r_reconciliation(payload, source_report_path=str(item)).ok:
            return item, payload
    return None, {}


def build_guarded_runtime_loop(settings: Any, source: Source30RReconciliationStatus) -> GuardedRuntimeLoopStatus:
    required = _boolish(_setting(settings, "paper_mode_runtime_guardrail_loop_required", True), True)
    requested_ticks = max(0, _int(_setting(settings, "paper_mode_runtime_guardrail_max_ticks", 3), 3))
    tick_cap = max(0, _int(_setting(settings, "paper_mode_runtime_guardrail_tick_cap", 5), 5))
    executed_ticks = min(requested_ticks, tick_cap)
    ticks: list[dict[str, Any]] = []
    for index in range(executed_ticks):
        ticks.append(GuardedRuntimeTick(
            index=index,
            event_type="paper_runtime_guardrail_tick",
            signal="HOLD",
            action="HOLD_GUARDED_NO_ORDER",
            order_action_performed=False,
            exchange_submit_performed=False,
            network_submit_attempted=False,
            notional_usd=0.0,
            reason_code="PAPER_RUNTIME_GUARDRAIL_NO_ORDER_ACTION",
        ).to_dict())
    order_actions = sum(1 for tick in ticks if _boolish(tick.get("order_action_performed"), False))
    exchange_submits = sum(1 for tick in ticks if _boolish(tick.get("exchange_submit_performed"), False))
    network_submits = sum(1 for tick in ticks if _boolish(tick.get("network_submit_attempted"), False))
    trading_actions = sum(1 for tick in ticks if str(tick.get("action")) != "HOLD_GUARDED_NO_ORDER")
    total_notional = sum(_float(tick.get("notional_usd"), 0.0) for tick in ticks)
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_RUNTIME_GUARDRAIL_LOOP_REQUIRED")
    if not source.ok:
        reasons.append("PAPER_RUNTIME_GUARDRAIL_SOURCE_30R_NOT_READY")
    if requested_ticks <= 0 or executed_ticks <= 0:
        reasons.append("PAPER_RUNTIME_GUARDRAIL_NO_TICKS_EXECUTED")
    if requested_ticks > tick_cap:
        reasons.append("PAPER_RUNTIME_GUARDRAIL_REQUESTED_TICKS_EXCEED_CAP")
    if order_actions or exchange_submits or network_submits or trading_actions or total_notional != 0.0:
        reasons.append("PAPER_RUNTIME_GUARDRAIL_LOOP_ACTION_OR_SUBMIT_DETECTED")
    return GuardedRuntimeLoopStatus(
        ok=required and not reasons,
        required=required,
        requested_ticks=requested_ticks,
        executed_ticks=executed_ticks,
        tick_cap=tick_cap,
        loop_completed=executed_ticks == requested_ticks and executed_ticks > 0,
        order_action_count=order_actions,
        exchange_submit_count=exchange_submits,
        network_submit_count=network_submits,
        trading_action_count=trading_actions,
        total_notional_usd=total_notional,
        ticks=ticks,
        reason_codes=reasons or ["GUARDED_PAPER_RUNTIME_LOOP_COMPLETED_NO_ORDER_ACTION"],
    )


def evaluate_strict_caps(settings: Any, loop: GuardedRuntimeLoopStatus) -> StrictCapsStatus:
    required = _boolish(_setting(settings, "paper_mode_runtime_guardrail_strict_caps_required", True), True)
    order_cap = max(0, _int(_setting(settings, "paper_mode_runtime_guardrail_order_action_cap", 0), 0))
    exchange_cap = max(0, _int(_setting(settings, "paper_mode_runtime_guardrail_exchange_submit_cap", 0), 0))
    network_cap = max(0, _int(_setting(settings, "paper_mode_runtime_guardrail_network_submit_cap", 0), 0))
    max_notional = max(0.0, _float(_setting(settings, "paper_mode_runtime_guardrail_max_notional_usd", 0.0), 0.0))
    seconds_cap = max(1, _int(_setting(settings, "paper_mode_runtime_guardrail_runtime_seconds_cap", 30), 30))
    observed_seconds = 0.0
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_RUNTIME_STRICT_CAPS_REQUIRED")
    if loop.executed_ticks > loop.tick_cap:
        reasons.append("PAPER_RUNTIME_TICK_CAP_EXCEEDED")
    if loop.order_action_count > order_cap:
        reasons.append("PAPER_RUNTIME_ORDER_ACTION_CAP_EXCEEDED")
    if loop.exchange_submit_count > exchange_cap:
        reasons.append("PAPER_RUNTIME_EXCHANGE_SUBMIT_CAP_EXCEEDED")
    if loop.network_submit_count > network_cap:
        reasons.append("PAPER_RUNTIME_NETWORK_SUBMIT_CAP_EXCEEDED")
    if loop.total_notional_usd > max_notional:
        reasons.append("PAPER_RUNTIME_NOTIONAL_CAP_EXCEEDED")
    if observed_seconds > seconds_cap:
        reasons.append("PAPER_RUNTIME_SECONDS_CAP_EXCEEDED")
    return StrictCapsStatus(
        ok=required and not reasons,
        required=required,
        tick_cap=loop.tick_cap,
        executed_ticks=loop.executed_ticks,
        order_action_cap=order_cap,
        observed_order_actions=loop.order_action_count,
        exchange_submit_cap=exchange_cap,
        observed_exchange_submits=loop.exchange_submit_count,
        network_submit_cap=network_cap,
        observed_network_submits=loop.network_submit_count,
        max_notional_usd=max_notional,
        observed_notional_usd=loop.total_notional_usd,
        runtime_seconds_cap=seconds_cap,
        observed_runtime_seconds=observed_seconds,
        reason_codes=reasons or ["STRICT_RUNTIME_CAPS_VERIFIED_ZERO_ORDER_ZERO_SUBMIT"],
    )


def evaluate_kill_switch_proof(settings: Any, caps: StrictCapsStatus) -> KillSwitchProofStatus:
    required = _boolish(_setting(settings, "paper_mode_runtime_guardrail_kill_switch_required", True), True)
    enabled = _boolish(_setting(settings, "paper_mode_runtime_guardrail_kill_switch_enabled", True), True)
    paper_blocked = _boolish(_setting(settings, "paper_order_enablement_still_blocked", True), True)
    runtime_blocked = _boolish(_setting(settings, "runtime_activation_blocked", True), True)
    order_cap_zero = caps.order_action_cap == 0
    exchange_cap_zero = caps.exchange_submit_cap == 0
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_RUNTIME_KILL_SWITCH_PROOF_REQUIRED")
    if not enabled:
        reasons.append("PAPER_RUNTIME_KILL_SWITCH_NOT_ENABLED")
    if not paper_blocked or not runtime_blocked:
        reasons.append("PAPER_RUNTIME_ENABLEMENT_NOT_BLOCKED")
    if not order_cap_zero or not exchange_cap_zero:
        reasons.append("PAPER_RUNTIME_KILL_SWITCH_CAPS_NOT_ZERO")
    return KillSwitchProofStatus(
        ok=required and enabled and paper_blocked and runtime_blocked and order_cap_zero and exchange_cap_zero and not reasons,
        required=required,
        kill_switch_enabled=enabled,
        paper_order_enablement_still_blocked=paper_blocked,
        runtime_activation_blocked=runtime_blocked,
        order_action_cap_zero=order_cap_zero,
        exchange_submit_cap_zero=exchange_cap_zero,
        reason_codes=reasons or ["KILL_SWITCH_PROOF_VERIFIED_PAPER_RUNTIME_GUARDRAIL"],
    )


def evaluate_no_exchange_submit(settings: Any, source: Source30RReconciliationStatus, loop: GuardedRuntimeLoopStatus) -> NoExchangeSubmitStatus:
    required = _boolish(_setting(settings, "paper_mode_runtime_guardrail_no_exchange_submit_required", True), True)
    approved_exchange = source.approved_for_exchange_submit
    exchange_submit = source.exchange_submit_performed or loop.exchange_submit_count > 0
    network_submit = source.network_submit_attempted or loop.network_submit_count > 0
    order_actions = source.order_actions_performed or loop.order_action_count > 0
    trading_actions = source.trading_action_performed or loop.trading_action_count > 0
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_RUNTIME_NO_EXCHANGE_SUBMIT_REQUIRED")
    if approved_exchange or exchange_submit or network_submit or order_actions or trading_actions:
        reasons.append("PAPER_RUNTIME_EXCHANGE_OR_ORDER_ACTION_DETECTED")
    return NoExchangeSubmitStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved_exchange,
        exchange_submit_performed=exchange_submit,
        network_submit_attempted=network_submit,
        order_actions_performed=order_actions,
        trading_action_performed=trading_actions,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED_PAPER_RUNTIME_GUARDRAIL"],
    )


def evaluate_no_live_real(settings: Any, source: Source30RReconciliationStatus) -> NoLiveRealStatus:
    required = _boolish(_setting(settings, "paper_mode_runtime_guardrail_no_live_real_required", True), True)
    live_armed = _boolish(_setting(settings, "live_trading_armed", False), False)
    live_confirm = _boolish(_setting(settings, "live_real_double_confirm", False), False)
    approved_live = source.approved_for_live_real
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_RUNTIME_NO_LIVE_REAL_REQUIRED")
    if approved_live or live_armed or live_confirm:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_ENABLED_OR_ARMED")
    return NoLiveRealStatus(
        ok=required and not reasons,
        required=required,
        approved_for_live_real=approved_live,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_confirm,
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_PAPER_RUNTIME_GUARDRAIL"],
    )


def build_paper_mode_runtime_guardrail_snapshot(settings: Any, source_30r_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> dict[str, Any]:
    source = evaluate_source_30r_reconciliation(source_30r_snapshot, source_report_path=source_report_path)
    loop = build_guarded_runtime_loop(settings, source)
    caps = evaluate_strict_caps(settings, loop)
    kill_switch = evaluate_kill_switch_proof(settings, caps)
    no_exchange = evaluate_no_exchange_submit(settings, source, loop)
    no_live = evaluate_no_live_real(settings, source)
    ready = source.ok and loop.ok and caps.ok and kill_switch.ok and no_exchange.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30R_REQUIRED_DECISION
    elif not loop.ok:
        decision = LOOP_NOT_READY_DECISION
    elif not caps.ok:
        decision = CAPS_NOT_READY_DECISION
    elif not kill_switch.ok:
        decision = KILL_SWITCH_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    reasons = [*source.reason_codes, *loop.reason_codes, *caps.reason_codes, *kill_switch.reason_codes, *no_exchange.reason_codes, *no_live.reason_codes]
    reasons.extend(["GUARDED_PAPER_RUNTIME_LOOP_PROOF", "STRICT_CAPS_PROOF", "KILL_SWITCH_PROOF", "NO_EXCHANGE_SUBMIT_PROOF", "NO_LIVE_REAL_VERIFIED"])
    payload = PaperModeRuntimeGuardrailDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_mode_runtime_guardrail=ready,
        approved_for_30r_reconciliation_consumption=source.ok,
        approved_for_guarded_runtime_loop=loop.ok,
        approved_for_strict_caps=caps.ok,
        approved_for_kill_switch_proof=kill_switch.ok,
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        source_30r_reconciliation_verified=source.ok,
        guarded_runtime_loop_verified=loop.ok,
        strict_caps_verified=caps.ok,
        kill_switch_verified=kill_switch.ok,
        no_exchange_submit_verified=no_exchange.ok,
        no_live_real_verified=no_live.ok,
        loop_tick_count=loop.executed_ticks,
        order_action_count=loop.order_action_count,
        exchange_submit_count=loop.exchange_submit_count,
        network_submit_count=loop.network_submit_count,
        mismatch_count=source.mismatch_count,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        order_actions_performed=False,
        exchange_submit_performed=False,
        network_submit_attempted=False,
        reason_codes=reasons,
        source_30r=source.to_dict(),
        guarded_runtime_loop=loop.to_dict(),
        strict_caps=caps.to_dict(),
        kill_switch_proof=kill_switch.to_dict(),
        no_exchange_submit=no_exchange.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30r_snapshot=dict(source_30r_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "report_type": REPORT_TYPE,
        "source_30r_reconciliation_gate": True,
        "guarded_runtime_loop_gate": True,
        "strict_caps_gate": True,
        "kill_switch_proof_gate": True,
        "no_exchange_submit_gate": True,
        "no_live_real_gate": True,
    })
    return payload


def build_from_latest_30r_reconciliation_report(settings: Any | None = None, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source = latest_valid_30r_reconciliation_report(reports_dir)
    return build_paper_mode_runtime_guardrail_snapshot(
        resolved_settings,
        source,
        source_report_path=str(source_path) if source_path else None,
    )


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, payload)
    lines = [
        f"# {CONTRACT_VERSION} Paper Mode Runtime Guardrail",
        "",
        "Consumes 30R reconciliation, runs guarded paper runtime loop, verifies strict caps and kill-switch proof, and keeps exchange submit/live-real blocked.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_paper_mode_runtime_guardrail`: `{payload.get('approved_for_paper_mode_runtime_guardrail')}`",
        f"- `source_30r_reconciliation_verified`: `{payload.get('source_30r_reconciliation_verified')}`",
        f"- `guarded_runtime_loop_verified`: `{payload.get('guarded_runtime_loop_verified')}`",
        f"- `strict_caps_verified`: `{payload.get('strict_caps_verified')}`",
        f"- `kill_switch_verified`: `{payload.get('kill_switch_verified')}`",
        f"- `loop_tick_count`: `{payload.get('loop_tick_count')}`",
        f"- `order_action_count`: `{payload.get('order_action_count')}`",
        f"- `exchange_submit_count`: `{payload.get('exchange_submit_count')}`",
        f"- `network_submit_count`: `{payload.get('network_submit_count')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
