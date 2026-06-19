from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

PAPER_CANDIDATE_PREFLIGHT_CONTRACT_VERSION = "4B.4.3.6.6.30A"
RUNTIME_ACTIVATION_BLOCKED_BY_PAPER_PREFLIGHT = True
PAPER_LIVE_ORDER_BLOCKED_BY_PAPER_PREFLIGHT = True
LIVE_REAL_HARD_BLOCKED_BY_PAPER_PREFLIGHT = True
TRAINING_RELOAD_BLOCKED_BY_PAPER_PREFLIGHT = True


@dataclass(frozen=True, slots=True)
class ExchangeSandboxStatus:
    ok: bool
    execution_mode: str
    market_type: str
    base_url: str
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperRiskLimits:
    ok: bool
    capital_cap_usd: float
    order_notional_cap_usd: float
    max_daily_loss_usd: float
    max_daily_trades_cap: int
    kill_switch_enabled: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperCandidatePreflightDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_no_order_to_paper_transition_preflight: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    production_readiness_evidence_complete: bool
    exchange_sandbox_isolated: bool
    capital_cap_verified: bool
    kill_switch_verified: bool
    operator_approval_required: bool
    operator_approval_verified: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    sandbox: dict[str, Any]
    risk_limits: dict[str, Any]
    production_readiness_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _csv(value: Any) -> set[str]:
    return {part.strip().lower() for part in str(value or "").split(",") if part.strip()}


def evaluate_exchange_sandbox_isolation(settings: Any) -> ExchangeSandboxStatus:
    execution_mode = str(_setting(settings, "execution_mode", "dry_run") or "").lower()
    market_type = str(_setting(settings, "market_type", "spot_demo") or "").lower()
    base_url = str(_setting(settings, "base_url", "") or "").lower()
    allowed_types = _csv(_setting(settings, "paper_sandbox_allowed_market_types", "spot_demo,spot_testnet"))
    reasons: list[str] = []
    if execution_mode == "live_real":
        reasons.append("EXECUTION_MODE_LIVE_REAL_BLOCKED")
    if market_type not in allowed_types:
        reasons.append("MARKET_TYPE_NOT_SANDBOX_ALLOWED")
    if not ("demo" in base_url or "testnet" in base_url or execution_mode == "dry_run"):
        reasons.append("BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    return ExchangeSandboxStatus(ok=not reasons, execution_mode=execution_mode, market_type=market_type, base_url=base_url, reason_codes=reasons or ["EXCHANGE_SANDBOX_ISOLATION_VERIFIED"])


def evaluate_paper_risk_limits(settings: Any) -> PaperRiskLimits:
    capital_cap = _float(_setting(settings, "paper_transition_capital_cap_usd", 100.0))
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", 25.0))
    max_daily_loss = _float(_setting(settings, "paper_max_daily_loss_usd", 5.0))
    max_daily_trades = _int(_setting(settings, "paper_max_daily_trades_cap", 5))
    kill_required = bool(_setting(settings, "paper_kill_switch_required", True))
    kill_enabled = bool(_setting(settings, "paper_kill_switch_enabled", True))
    reasons: list[str] = []
    if capital_cap <= 0:
        reasons.append("PAPER_CAPITAL_CAP_NOT_POSITIVE")
    if order_cap <= 0:
        reasons.append("PAPER_ORDER_NOTIONAL_CAP_NOT_POSITIVE")
    if capital_cap > 0 and order_cap > capital_cap:
        reasons.append("PAPER_ORDER_CAP_EXCEEDS_CAPITAL_CAP")
    if max_daily_loss <= 0:
        reasons.append("PAPER_MAX_DAILY_LOSS_NOT_POSITIVE")
    if capital_cap > 0 and max_daily_loss > capital_cap:
        reasons.append("PAPER_MAX_DAILY_LOSS_EXCEEDS_CAPITAL_CAP")
    if max_daily_trades <= 0:
        reasons.append("PAPER_MAX_DAILY_TRADES_NOT_POSITIVE")
    if kill_required and not kill_enabled:
        reasons.append("PAPER_KILL_SWITCH_REQUIRED_NOT_ENABLED")
    return PaperRiskLimits(ok=not reasons, capital_cap_usd=capital_cap, order_notional_cap_usd=order_cap, max_daily_loss_usd=max_daily_loss, max_daily_trades_cap=max_daily_trades, kill_switch_enabled=kill_enabled, reason_codes=reasons or ["PAPER_RISK_LIMITS_VERIFIED"])


def _production_readiness_ok(snapshot: Mapping[str, Any]) -> bool:
    return bool(snapshot.get("evidence_complete")) and bool(snapshot.get("approved_for_paper_candidate_preflight")) and str(snapshot.get("decision") or "") == "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED"


def _operator_approved(settings: Any, supplied_confirmation: str | None = None) -> bool:
    required = bool(_setting(settings, "paper_transition_operator_approval_required", True))
    if not required:
        return True
    approved_flag = bool(_setting(settings, "paper_transition_operator_approved", False))
    expected = str(_setting(settings, "paper_transition_confirmation_phrase", "CONFIRM_PAPER_TRANSITION_CANDIDATE") or "").strip()
    configured_token = str(_setting(settings, "paper_transition_confirmation_token", "") or "").strip()
    supplied = str(supplied_confirmation or configured_token or "").strip()
    return approved_flag and bool(expected) and supplied == expected


def evaluate_paper_candidate_preflight(
    settings: Any,
    production_readiness_snapshot: Mapping[str, Any],
    *,
    supplied_operator_confirmation: str | None = None,
) -> PaperCandidatePreflightDecision:
    sandbox = evaluate_exchange_sandbox_isolation(settings)
    limits = evaluate_paper_risk_limits(settings)
    production_ready = _production_readiness_ok(production_readiness_snapshot)
    operator_required = bool(_setting(settings, "paper_transition_operator_approval_required", True))
    operator_ok = _operator_approved(settings, supplied_operator_confirmation)
    preflight_ready = production_ready and sandbox.ok and limits.ok
    transition_candidate = preflight_ready and (operator_ok or not operator_required)
    reasons: list[str] = []
    reasons.append("PRODUCTION_READINESS_CONSOLIDATION_ACCEPTED" if production_ready else "PRODUCTION_READINESS_CONSOLIDATION_REQUIRED")
    reasons.extend(sandbox.reason_codes)
    reasons.extend(limits.reason_codes)
    if preflight_ready:
        reasons.append("NO_ORDER_TO_PAPER_PREFLIGHT_READY")
    if operator_required and not operator_ok:
        reasons.append("OPERATOR_APPROVAL_REQUIRED_FOR_PAPER_TRANSITION_CANDIDATE")
    if transition_candidate:
        reasons.append("PAPER_TRANSITION_CANDIDATE_REVIEW_ONLY")
    reasons.append("PAPER_ORDER_ENABLEMENT_STILL_BLOCKED")
    reasons.append("LIVE_REAL_HARD_BLOCK_VERIFIED")
    decision = "PAPER_CANDIDATE_PREFLIGHT_READY_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED" if preflight_ready and not transition_candidate else ("PAPER_TRANSITION_CANDIDATE_REVIEW_ONLY_LIVE_REAL_BLOCKED" if transition_candidate else "PAPER_CANDIDATE_PREFLIGHT_NOT_READY")
    return PaperCandidatePreflightDecision(
        contract_version=PAPER_CANDIDATE_PREFLIGHT_CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_no_order_to_paper_transition_preflight=preflight_ready,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        production_readiness_evidence_complete=production_ready,
        exchange_sandbox_isolated=sandbox.ok,
        capital_cap_verified=limits.ok,
        kill_switch_verified=limits.kill_switch_enabled,
        operator_approval_required=operator_required,
        operator_approval_verified=operator_ok,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        sandbox=sandbox.to_dict(),
        risk_limits=limits.to_dict(),
        production_readiness_snapshot=dict(production_readiness_snapshot),
    )


def build_paper_candidate_preflight_snapshot(settings: Any, production_readiness_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    decision = evaluate_paper_candidate_preflight(settings, production_readiness_snapshot)
    payload = decision.to_dict()
    payload.update({
        "read_only": True,
        "paper_candidate_preflight": True,
        "no_order_to_paper_transition_gate": True,
        "exchange_sandbox_isolation_gate": True,
        "capital_cap_gate": True,
        "kill_switch_gate": True,
        "operator_approval_gate": True,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    })
    return payload
