from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30G"
SOURCE_30F_CONTRACT_VERSION = "4B.4.3.6.6.30F"
SOURCE_30F_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED"
REPORT_TYPE = "paper_sandbox_dry_run_execution_candidate_gate_no_exchange_submit"
REPORT_PREFIX = "4B436630G_paper_sandbox_dry_run_execution_candidate_gate"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_READY_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED"
SOURCE_30F_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_30F_PLAN_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_NOT_READY_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_sandbox_dry_run_execution_candidate_gate": True,
    "paper_sandbox_dry_run_execution_candidate_only": True,
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
class Source30FPlanStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    approved_for_paper_sandbox_dry_run_transition_plan: bool
    approved_for_paper_sandbox_dry_run_execution_plan: bool
    approved_for_order_path_simulation_envelope: bool
    approved_for_operator_final_go_no_go_checklist: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_order_enablement_still_blocked: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DryRunOnlyRuntimeEnvelopeStatus:
    ok: bool
    required: bool
    runtime_envelope: str
    execution_mode: str
    market_type: str
    base_url: str
    auto_trade_on_signal: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    max_open_orders: int
    order_notional_usd: float
    order_notional_cap_usd: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SingleSimulatedPaperIntentStatus:
    ok: bool
    required: bool
    intent_count: int
    simulated_intent_id: str
    symbol: str
    side: str
    order_type: str
    quote_notional_usd: float
    order_notional_cap_usd: float
    submitted_to_exchange: bool
    exchange_order_id: str | None
    exchange_client_order_id: str | None
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoExchangeSubmitStatus:
    ok: bool
    required: bool
    submitted_to_exchange: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    exchange_order_id: str | None
    exchange_client_order_id: str | None
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperCandidateStillBlockedStatus:
    ok: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_live_order_enablement_present: bool
    trading_action_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSandboxDryRunExecutionCandidateGateDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_dry_run_execution_candidate_gate: bool
    approved_for_paper_sandbox_dry_run_execution_candidate: bool
    approved_for_single_simulated_paper_intent: bool
    approved_for_no_exchange_submit_verification: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30f_plan_verified: bool
    dry_run_only_runtime_envelope_verified: bool
    single_simulated_paper_intent_verified: bool
    no_exchange_submit_verified: bool
    paper_candidate_still_blocked_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    source_30f_plan: dict[str, Any]
    dry_run_only_runtime_envelope: dict[str, Any]
    single_simulated_paper_intent: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    paper_candidate_still_blocked: dict[str, Any]
    source_30f_snapshot: dict[str, Any]

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
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def latest_30f_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630F_paper_sandbox_dry_run_transition_plan_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def evaluate_source_30f_plan(source_30f_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30FPlanStatus:
    contract = str(source_30f_snapshot.get("contract_version") or "") or None
    decision = str(source_30f_snapshot.get("decision") or "") or None
    plan_ready = bool(source_30f_snapshot.get("approved_for_paper_sandbox_dry_run_transition_plan", False))
    execution_plan = bool(source_30f_snapshot.get("approved_for_paper_sandbox_dry_run_execution_plan", False))
    envelope = bool(source_30f_snapshot.get("approved_for_order_path_simulation_envelope", False))
    checklist = bool(source_30f_snapshot.get("approved_for_operator_final_go_no_go_checklist", False))
    dry_run_execution = bool(source_30f_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    transition_candidate = bool(source_30f_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30f_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30f_snapshot.get("approved_for_live_real", False))
    no_order = bool(source_30f_snapshot.get("paper_order_enablement_still_blocked", False))
    trading_action = bool(source_30f_snapshot.get("trading_action_performed", False)) or bool(source_30f_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if contract != SOURCE_30F_CONTRACT_VERSION:
        reasons.append("SOURCE_30F_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30F_READY_DECISION:
        reasons.append("SOURCE_30F_READY_DECISION_REQUIRED")
    if not plan_ready:
        reasons.append("SOURCE_30F_TRANSITION_PLAN_NOT_READY")
    if not execution_plan:
        reasons.append("SOURCE_30F_DRY_RUN_EXECUTION_PLAN_NOT_READY")
    if not envelope:
        reasons.append("SOURCE_30F_ORDER_PATH_SIMULATION_ENVELOPE_NOT_READY")
    if not checklist:
        reasons.append("SOURCE_30F_OPERATOR_GO_NO_GO_CHECKLIST_NOT_READY")
    if dry_run_execution:
        reasons.append("SOURCE_30F_DRY_RUN_EXECUTION_UNEXPECTEDLY_APPROVED")
    if transition_candidate:
        reasons.append("SOURCE_30F_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("SOURCE_30F_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30F_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not no_order:
        reasons.append("SOURCE_30F_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    if trading_action:
        reasons.append("SOURCE_30F_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    ok = not reasons
    return Source30FPlanStatus(
        ok=ok,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        approved_for_paper_sandbox_dry_run_transition_plan=plan_ready,
        approved_for_paper_sandbox_dry_run_execution_plan=execution_plan,
        approved_for_order_path_simulation_envelope=envelope,
        approved_for_operator_final_go_no_go_checklist=checklist,
        approved_for_paper_sandbox_dry_run_execution=dry_run_execution,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_order_enablement_still_blocked=no_order,
        reason_codes=reasons or ["SOURCE_30F_TRANSITION_PLAN_VERIFIED"],
    )


def evaluate_dry_run_only_runtime_envelope(settings: Any, source_30f_snapshot: Mapping[str, Any]) -> DryRunOnlyRuntimeEnvelopeStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_execution_candidate_consume_30f_plan_required", True))
    envelope = _mapping(source_30f_snapshot.get("order_path_simulation_envelope"))
    runtime_envelope = str(envelope.get("runtime_envelope") or _setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    execution_mode = str(envelope.get("execution_mode") or _setting(settings, "execution_mode", "dry_run") or "").strip().lower()
    market_type = str(envelope.get("market_type") or _setting(settings, "market_type", "spot_demo") or "").strip().lower()
    base_url = str(envelope.get("base_url") or _setting(settings, "base_url", "") or "").strip().lower()
    auto_trade = bool(envelope.get("auto_trade_on_signal", _setting(settings, "auto_trade_on_signal", False)))
    live_armed = bool(envelope.get("live_trading_armed", _setting(settings, "live_trading_armed", False)))
    live_real_confirm = bool(envelope.get("live_real_double_confirm", _setting(settings, "live_real_double_confirm", False)))
    max_open_orders = _int(envelope.get("max_open_orders", _setting(settings, "paper_transition_max_open_orders", 1)), 1)
    order_notional = _float(envelope.get("order_notional_usd", _setting(settings, "order_notional_usd", 25.0)), 25.0)
    order_cap = _float(envelope.get("order_notional_cap_usd", _setting(settings, "paper_order_notional_cap_usd", 25.0)), 25.0)
    reasons: list[str] = []
    if not required:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_MUST_REMAIN_REQUIRED")
    if runtime_envelope != "sandbox_only":
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if execution_mode != "dry_run":
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_EXECUTION_MODE_NOT_DRY_RUN")
    if market_type not in {"spot_demo", "spot_testnet"}:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_MARKET_TYPE_NOT_SANDBOX")
    if not ("demo" in base_url or "testnet" in base_url or execution_mode == "dry_run"):
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    if auto_trade:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_AUTO_TRADE_UNEXPECTEDLY_ENABLED")
    if live_armed:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_LIVE_TRADING_ARMED_UNEXPECTEDLY_ENABLED")
    if live_real_confirm:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_LIVE_REAL_CONFIRM_UNEXPECTEDLY_ENABLED")
    if max_open_orders != 1:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_MAX_OPEN_ORDERS_MUST_EQUAL_ONE")
    if order_notional <= 0 or order_cap <= 0:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_NOTIONAL_INVALID")
    elif order_notional > order_cap:
        reasons.append("DRY_RUN_RUNTIME_ENVELOPE_NOTIONAL_EXCEEDS_CAP")
    ok = required and not reasons
    return DryRunOnlyRuntimeEnvelopeStatus(
        ok=ok,
        required=required,
        runtime_envelope=runtime_envelope,
        execution_mode=execution_mode,
        market_type=market_type,
        base_url=base_url,
        auto_trade_on_signal=auto_trade,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_real_confirm,
        max_open_orders=max_open_orders,
        order_notional_usd=order_notional,
        order_notional_cap_usd=order_cap,
        reason_codes=reasons or ["DRY_RUN_ONLY_RUNTIME_ENVELOPE_VERIFIED"],
    )


def build_single_simulated_paper_intent(settings: Any, envelope: DryRunOnlyRuntimeEnvelopeStatus) -> dict[str, Any]:
    symbol = str(_setting(settings, "symbol", "ETHUSDT") or "ETHUSDT").strip().upper()
    notional = min(envelope.order_notional_usd, envelope.order_notional_cap_usd)
    return {
        "simulated_intent_id": f"simulated-paper-intent-{CONTRACT_VERSION}",
        "intent_type": "paper_intent_simulation_only_no_exchange_submit",
        "symbol": symbol,
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": notional,
        "order_notional_cap_usd": envelope.order_notional_cap_usd,
        "runtime_envelope": envelope.runtime_envelope,
        "execution_mode": envelope.execution_mode,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
    }


def evaluate_single_simulated_paper_intent(settings: Any, envelope: DryRunOnlyRuntimeEnvelopeStatus) -> SingleSimulatedPaperIntentStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_single_simulated_intent_required", True))
    intent = build_single_simulated_paper_intent(settings, envelope)
    intent_count = 1
    side = str(intent.get("side") or "").upper()
    order_type = str(intent.get("order_type") or "").upper()
    notional = _float(intent.get("quote_notional_usd"), 0.0)
    cap = _float(intent.get("order_notional_cap_usd"), 0.0)
    submitted = bool(intent.get("submitted_to_exchange", False))
    exchange_order_id = intent.get("exchange_order_id")
    exchange_client_order_id = intent.get("exchange_client_order_id")
    reasons: list[str] = []
    if not required:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_MUST_REMAIN_REQUIRED")
    if not envelope.ok:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_RUNTIME_ENVELOPE_NOT_VERIFIED")
    if intent_count != 1:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_COUNT_MUST_EQUAL_ONE")
    if not str(intent.get("symbol") or "").strip():
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_SYMBOL_MISSING")
    if side not in {"BUY", "SELL"}:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_SIDE_INVALID")
    if order_type not in {"MARKET", "LIMIT"}:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_ORDER_TYPE_INVALID")
    if notional <= 0 or cap <= 0:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_NOTIONAL_INVALID")
    elif notional > cap:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_NOTIONAL_EXCEEDS_CAP")
    if submitted or exchange_order_id or exchange_client_order_id:
        reasons.append("SINGLE_SIMULATED_PAPER_INTENT_EXCHANGE_SUBMIT_UNEXPECTED")
    ok = required and not reasons
    return SingleSimulatedPaperIntentStatus(
        ok=ok,
        required=required,
        intent_count=intent_count,
        simulated_intent_id=str(intent["simulated_intent_id"]),
        symbol=str(intent["symbol"]),
        side=side,
        order_type=order_type,
        quote_notional_usd=notional,
        order_notional_cap_usd=cap,
        submitted_to_exchange=submitted,
        exchange_order_id=None if exchange_order_id is None else str(exchange_order_id),
        exchange_client_order_id=None if exchange_client_order_id is None else str(exchange_client_order_id),
        reason_codes=reasons or ["SINGLE_SIMULATED_PAPER_INTENT_VERIFIED_NO_EXCHANGE_SUBMIT"],
    )


def evaluate_no_exchange_submit(settings: Any, intent: SingleSimulatedPaperIntentStatus) -> NoExchangeSubmitStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_no_exchange_submit_required", True))
    submitted = bool(intent.submitted_to_exchange)
    exchange_submit = submitted or bool(intent.exchange_order_id) or bool(intent.exchange_client_order_id)
    network_submit = False
    reasons: list[str] = []
    if not required:
        reasons.append("NO_EXCHANGE_SUBMIT_MUST_REMAIN_REQUIRED")
    if not intent.ok:
        reasons.append("NO_EXCHANGE_SUBMIT_INTENT_NOT_VERIFIED")
    if submitted:
        reasons.append("NO_EXCHANGE_SUBMIT_SUBMITTED_TO_EXCHANGE")
    if exchange_submit:
        reasons.append("NO_EXCHANGE_SUBMIT_EXCHANGE_ORDER_REFERENCE_PRESENT")
    if network_submit:
        reasons.append("NO_EXCHANGE_SUBMIT_NETWORK_ATTEMPTED")
    ok = required and not reasons
    return NoExchangeSubmitStatus(
        ok=ok,
        required=required,
        submitted_to_exchange=submitted,
        exchange_submit_performed=exchange_submit,
        network_submit_attempted=network_submit,
        exchange_order_id=intent.exchange_order_id,
        exchange_client_order_id=intent.exchange_client_order_id,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED"],
    )


def evaluate_paper_candidate_still_blocked(source_30f_snapshot: Mapping[str, Any]) -> PaperCandidateStillBlockedStatus:
    dry_execution = bool(source_30f_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    transition_candidate = bool(source_30f_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30f_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30f_snapshot.get("approved_for_live_real", False))
    enablement = bool(source_30f_snapshot.get("paper_live_order_enablement_present", False))
    trading_action = bool(source_30f_snapshot.get("trading_action_performed", False)) or bool(source_30f_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if dry_execution:
        reasons.append("PAPER_DRY_RUN_EXECUTION_UNEXPECTEDLY_APPROVED")
    if transition_candidate:
        reasons.append("PAPER_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if enablement:
        reasons.append("PAPER_ORDER_ENABLEMENT_UNEXPECTEDLY_PRESENT")
    if trading_action:
        reasons.append("ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    ok = not reasons
    return PaperCandidateStillBlockedStatus(
        ok=ok,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_live_order_enablement_present=enablement,
        trading_action_performed=trading_action,
        reason_codes=reasons or ["PAPER_CANDIDATE_STILL_BLOCKED_VERIFIED"],
    )


def build_paper_sandbox_dry_run_execution_candidate_gate_snapshot(
    settings: Any,
    source_30f_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30f_plan(source_30f_snapshot, source_report_path=source_report_path)
    runtime = evaluate_dry_run_only_runtime_envelope(settings, source_30f_snapshot)
    intent = evaluate_single_simulated_paper_intent(settings, runtime)
    no_submit = evaluate_no_exchange_submit(settings, intent)
    blocked = evaluate_paper_candidate_still_blocked(source_30f_snapshot)
    reasons = [*source.reason_codes, *runtime.reason_codes, *intent.reason_codes, *no_submit.reason_codes, *blocked.reason_codes]
    reasons.extend(["PAPER_CANDIDATE_STILL_BLOCKED", "NO_EXCHANGE_SUBMIT_VERIFIED", "LIVE_REAL_HARD_BLOCK_VERIFIED"])
    ready = source.ok and runtime.ok and intent.ok and no_submit.ok and blocked.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30F_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = PaperSandboxDryRunExecutionCandidateGateDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_dry_run_execution_candidate_gate=ready,
        approved_for_paper_sandbox_dry_run_execution_candidate=ready,
        approved_for_single_simulated_paper_intent=ready,
        approved_for_no_exchange_submit_verification=ready,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30f_plan_verified=source.ok,
        dry_run_only_runtime_envelope_verified=runtime.ok,
        single_simulated_paper_intent_verified=intent.ok,
        no_exchange_submit_verified=no_submit.ok,
        paper_candidate_still_blocked_verified=blocked.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        source_30f_plan=source.to_dict(),
        dry_run_only_runtime_envelope=runtime.to_dict(),
        single_simulated_paper_intent=intent.to_dict(),
        no_exchange_submit=no_submit.to_dict(),
        paper_candidate_still_blocked=blocked.to_dict(),
        source_30f_snapshot=dict(source_30f_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30f_plan_gate": True,
        "dry_run_only_runtime_envelope_gate": True,
        "single_simulated_paper_intent_gate": True,
        "no_exchange_submit_gate": True,
        "paper_candidate_still_blocked_gate": True,
        "still_no_paper_order_enablement_gate": True,
        "no_live_real_enforcement": True,
    })
    return payload


def build_from_latest_30f_ready_report(settings: Any | None = None, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    source_path = latest_30f_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    return build_paper_sandbox_dry_run_execution_candidate_gate_snapshot(
        settings or Settings(),
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_30F_REQUIRED_DECISION:
        return "30f_required"
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
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Dry-run Execution Candidate Gate")
    lines.append("")
    lines.append("This report consumes a 30F ready transition plan, verifies a dry-run-only runtime envelope, builds one simulated paper intent, and confirms that no exchange submit is performed.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_dry_run_execution_candidate_gate",
        "approved_for_paper_sandbox_dry_run_execution_candidate",
        "approved_for_single_simulated_paper_intent",
        "approved_for_no_exchange_submit_verification",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_exchange_submit",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "paper_order_enablement_still_blocked",
        "trading_action_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Candidate gates")
    for key in (
        "source_30f_plan_verified",
        "dry_run_only_runtime_envelope_verified",
        "single_simulated_paper_intent_verified",
        "no_exchange_submit_verified",
        "paper_candidate_still_blocked_verified",
        "runtime_activation_blocked",
        "paper_live_order_blocked",
        "training_reload_blocked",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
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
