from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping

PAPER_TRANSITION_OPERATOR_GATE_CONTRACT_VERSION = "4B.4.3.6.6.30B"
RUNTIME_ACTIVATION_BLOCKED_BY_PAPER_TRANSITION_GATE = True
PAPER_LIVE_ORDER_BLOCKED_BY_PAPER_TRANSITION_GATE = True
LIVE_REAL_HARD_BLOCKED_BY_PAPER_TRANSITION_GATE = True
TRAINING_RELOAD_BLOCKED_BY_PAPER_TRANSITION_GATE = True

READY_DECISION = "PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_READY_REVIEW_ONLY_LIVE_REAL_BLOCKED"
APPROVAL_REQUIRED_DECISION = "PAPER_TRANSITION_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_NOT_READY_LIVE_REAL_BLOCKED"


@dataclass(frozen=True, slots=True)
class TypedApprovalStatus:
    ok: bool
    operator_required: bool
    operator_approved: bool
    operator_id: str
    token_match: bool
    ttl_sec: int
    issued_at_ms: int
    expires_at_ms: int
    now_ms: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SandboxRuntimeEnvelopeStatus:
    ok: bool
    runtime_envelope: str
    execution_mode: str
    market_type: str
    base_url: str
    auto_trade_on_signal: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    order_notional_usd: float
    order_notional_cap_usd: float
    max_open_orders: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperDryRunReconciliationProbeStatus:
    ok: bool
    required: bool
    probe_passed: bool
    order_actions_performed: bool
    paper_live_order_enablement_present: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperTransitionOperatorGateDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_transition_operator_approval_gate: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    paper_candidate_preflight_ready: bool
    operator_approval_verified: bool
    sandbox_runtime_envelope_verified: bool
    paper_dry_run_reconciliation_probe_verified: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    typed_approval: dict[str, Any]
    sandbox_runtime_envelope: dict[str, Any]
    dry_run_reconciliation_probe: dict[str, Any]
    paper_preflight_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _now_ms() -> int:
    return int(time.time() * 1000)


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


def _csv(value: Any) -> set[str]:
    return {part.strip().lower() for part in str(value or "").split(",") if part.strip()}


def _paper_preflight_ready(snapshot: Mapping[str, Any]) -> bool:
    return (
        bool(snapshot.get("approved_for_no_order_to_paper_transition_preflight", False))
        and not bool(snapshot.get("approved_for_paper_candidate", False))
        and not bool(snapshot.get("approved_for_live_real", False))
        and bool(snapshot.get("paper_live_order_blocked", True))
    )


def evaluate_typed_operator_approval(
    settings: Any,
    *,
    supplied_operator_confirmation: str | None = None,
    now_ms: int | None = None,
) -> TypedApprovalStatus:
    now = int(now_ms if now_ms is not None else _now_ms())
    required = bool(_setting(settings, "paper_transition_operator_approval_required", True))
    approved_flag = bool(_setting(settings, "paper_transition_operator_approved", False))
    operator_id = str(_setting(settings, "paper_transition_operator_id", "") or "").strip()
    expected = str(_setting(settings, "paper_transition_confirmation_phrase", "CONFIRM_PAPER_TRANSITION_CANDIDATE") or "").strip()
    configured_token = str(_setting(settings, "paper_transition_confirmation_token", "") or "").strip()
    supplied = str(supplied_operator_confirmation or configured_token or "").strip()
    ttl_sec = max(_int(_setting(settings, "paper_transition_approval_ttl_sec", 900), 900), 1)
    issued_at = _int(_setting(settings, "paper_transition_approval_issued_at_ms", 0), 0)
    expires_at = issued_at + ttl_sec * 1000 if issued_at > 0 else 0
    token_match = bool(expected) and supplied == expected
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_TRANSITION_OPERATOR_APPROVAL_MUST_REMAIN_REQUIRED")
    if not approved_flag:
        reasons.append("PAPER_TRANSITION_OPERATOR_APPROVED_FLAG_FALSE")
    if not operator_id:
        reasons.append("PAPER_TRANSITION_OPERATOR_ID_MISSING")
    if not token_match:
        reasons.append("PAPER_TRANSITION_CONFIRMATION_TOKEN_MISMATCH")
    if issued_at <= 0:
        reasons.append("PAPER_TRANSITION_APPROVAL_ISSUED_AT_MISSING")
    elif now > expires_at:
        reasons.append("PAPER_TRANSITION_APPROVAL_TOKEN_EXPIRED")
    ok = required and approved_flag and bool(operator_id) and token_match and issued_at > 0 and now <= expires_at
    return TypedApprovalStatus(
        ok=ok,
        operator_required=required,
        operator_approved=approved_flag,
        operator_id=operator_id,
        token_match=token_match,
        ttl_sec=ttl_sec,
        issued_at_ms=issued_at,
        expires_at_ms=expires_at,
        now_ms=now,
        reason_codes=reasons or ["PAPER_TRANSITION_TYPED_OPERATOR_APPROVAL_VERIFIED"],
    )


def evaluate_sandbox_runtime_envelope(settings: Any) -> SandboxRuntimeEnvelopeStatus:
    runtime_envelope = str(_setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    execution_mode = str(_setting(settings, "execution_mode", "dry_run") or "").strip().lower()
    market_type = str(_setting(settings, "market_type", "spot_demo") or "").strip().lower()
    base_url = str(_setting(settings, "base_url", "") or "").strip().lower()
    auto_trade = bool(_setting(settings, "auto_trade_on_signal", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_real_double_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    allowed_types = _csv(_setting(settings, "paper_sandbox_allowed_market_types", "spot_demo,spot_testnet"))
    order_notional = _float(_setting(settings, "order_notional_usd", 25.0), 25.0)
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", 25.0), 25.0)
    max_open_orders = _int(_setting(settings, "paper_transition_max_open_orders", 1), 1)
    reasons: list[str] = []
    if runtime_envelope != "sandbox_only":
        reasons.append("PAPER_TRANSITION_RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if execution_mode == "live_real":
        reasons.append("PAPER_TRANSITION_EXECUTION_MODE_LIVE_REAL_BLOCKED")
    if market_type not in allowed_types:
        reasons.append("PAPER_TRANSITION_MARKET_TYPE_NOT_SANDBOX_ALLOWED")
    if not (execution_mode == "dry_run" or "demo" in base_url or "testnet" in base_url):
        reasons.append("PAPER_TRANSITION_BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    if auto_trade:
        reasons.append("PAPER_TRANSITION_AUTO_TRADE_MUST_REMAIN_DISABLED")
    if live_armed:
        reasons.append("PAPER_TRANSITION_LIVE_TRADING_ARMED_BLOCKED")
    if live_real_double_confirm:
        reasons.append("PAPER_TRANSITION_LIVE_REAL_DOUBLE_CONFIRM_BLOCKED")
    if order_notional <= 0 or order_cap <= 0:
        reasons.append("PAPER_TRANSITION_ORDER_NOTIONAL_INVALID")
    elif order_notional > order_cap:
        reasons.append("PAPER_TRANSITION_ORDER_NOTIONAL_EXCEEDS_CAP")
    if max_open_orders <= 0:
        reasons.append("PAPER_TRANSITION_MAX_OPEN_ORDERS_INVALID")
    ok = not reasons
    return SandboxRuntimeEnvelopeStatus(
        ok=ok,
        runtime_envelope=runtime_envelope,
        execution_mode=execution_mode,
        market_type=market_type,
        base_url=base_url,
        auto_trade_on_signal=auto_trade,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_real_double_confirm,
        order_notional_usd=order_notional,
        order_notional_cap_usd=order_cap,
        max_open_orders=max_open_orders,
        reason_codes=reasons or ["PAPER_TRANSITION_SANDBOX_ONLY_RUNTIME_ENVELOPE_VERIFIED"],
    )


def evaluate_paper_dry_run_reconciliation_probe(settings: Any) -> PaperDryRunReconciliationProbeStatus:
    required = bool(_setting(settings, "paper_transition_dry_run_reconciliation_required", True))
    probe_passed = bool(_setting(settings, "paper_transition_dry_run_reconciliation_probe_passed", True))
    order_actions = bool(_setting(settings, "paper_transition_dry_run_probe_order_actions_performed", False))
    paper_enablement = bool(_setting(settings, "paper_live_order_enablement_present", False))
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_DRY_RUN_RECONCILIATION_PROBE_MUST_REMAIN_REQUIRED")
    if not probe_passed:
        reasons.append("PAPER_DRY_RUN_RECONCILIATION_PROBE_NOT_PASSED")
    if order_actions:
        reasons.append("PAPER_DRY_RUN_RECONCILIATION_PROBE_PERFORMED_ORDER_ACTION")
    if paper_enablement:
        reasons.append("PAPER_LIVE_ORDER_ENABLEMENT_UNEXPECTEDLY_PRESENT")
    ok = required and probe_passed and not order_actions and not paper_enablement
    return PaperDryRunReconciliationProbeStatus(
        ok=ok,
        required=required,
        probe_passed=probe_passed,
        order_actions_performed=order_actions,
        paper_live_order_enablement_present=paper_enablement,
        reason_codes=reasons or ["PAPER_DRY_RUN_RECONCILIATION_PROBE_VERIFIED_NO_ORDER"],
    )


def evaluate_paper_transition_operator_gate(
    settings: Any,
    paper_preflight_snapshot: Mapping[str, Any],
    *,
    supplied_operator_confirmation: str | None = None,
    now_ms: int | None = None,
) -> PaperTransitionOperatorGateDecision:
    typed = evaluate_typed_operator_approval(settings, supplied_operator_confirmation=supplied_operator_confirmation, now_ms=now_ms)
    envelope = evaluate_sandbox_runtime_envelope(settings)
    probe = evaluate_paper_dry_run_reconciliation_probe(settings)
    preflight_ready = _paper_preflight_ready(paper_preflight_snapshot)
    gate_ready = preflight_ready and envelope.ok and probe.ok
    transition_candidate = gate_ready and typed.ok
    reasons: list[str] = []
    reasons.append("PAPER_CANDIDATE_PREFLIGHT_ACCEPTED" if preflight_ready else "PAPER_CANDIDATE_PREFLIGHT_REQUIRED")
    reasons.extend(envelope.reason_codes)
    reasons.extend(probe.reason_codes)
    reasons.extend(typed.reason_codes)
    if gate_ready and not typed.ok:
        reasons.append("PAPER_TRANSITION_OPERATOR_APPROVAL_REQUIRED")
    if transition_candidate:
        reasons.append("PAPER_TRANSITION_CANDIDATE_REVIEW_ONLY")
    reasons.append("PAPER_ORDER_ENABLEMENT_STILL_BLOCKED")
    reasons.append("LIVE_REAL_HARD_BLOCK_VERIFIED")
    decision = READY_DECISION if transition_candidate else (APPROVAL_REQUIRED_DECISION if gate_ready else NOT_READY_DECISION)
    return PaperTransitionOperatorGateDecision(
        contract_version=PAPER_TRANSITION_OPERATOR_GATE_CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_transition_operator_approval_gate=gate_ready,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        paper_candidate_preflight_ready=preflight_ready,
        operator_approval_verified=typed.ok,
        sandbox_runtime_envelope_verified=envelope.ok,
        paper_dry_run_reconciliation_probe_verified=probe.ok,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        typed_approval=typed.to_dict(),
        sandbox_runtime_envelope=envelope.to_dict(),
        dry_run_reconciliation_probe=probe.to_dict(),
        paper_preflight_snapshot=dict(paper_preflight_snapshot),
    )


def build_paper_transition_operator_gate_snapshot(
    settings: Any,
    paper_preflight_snapshot: Mapping[str, Any],
    *,
    supplied_operator_confirmation: str | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    decision = evaluate_paper_transition_operator_gate(settings, paper_preflight_snapshot, supplied_operator_confirmation=supplied_operator_confirmation, now_ms=now_ms)
    payload = decision.to_dict()
    payload.update({
        "read_only": True,
        "paper_transition_operator_approval_gate": True,
        "typed_approval_token_gate": True,
        "sandbox_only_runtime_envelope_gate": True,
        "paper_dry_run_reconciliation_probe_gate": True,
        "no_live_real_enforcement": True,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    })
    return payload
