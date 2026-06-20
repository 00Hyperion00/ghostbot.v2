from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.30C"
SOURCE_30B_CONTRACT_VERSION = "4B.4.3.6.6.30B"
REPORT_TYPE = "paper_transition_candidate_review_still_no_paper_order_enablement"
REPORT_PREFIX = "4B436630C_paper_transition_candidate_review"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_TRANSITION_CANDIDATE_REVIEW_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED"
OPERATOR_EVIDENCE_REQUIRED_DECISION = "PAPER_TRANSITION_CANDIDATE_REVIEW_OPERATOR_APPROVAL_EVIDENCE_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_TRANSITION_CANDIDATE_REVIEW_NOT_READY_LIVE_REAL_BLOCKED"

SOURCE_30B_READY_DECISION = "PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_READY_REVIEW_ONLY_LIVE_REAL_BLOCKED"
SOURCE_30B_DEFAULT_DECISION = "PAPER_TRANSITION_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_transition_candidate_review": True,
    "paper_candidate_still_blocked": True,
    "paper_live_order_blocked": True,
    "live_real_blocked": True,
    "runtime_activation_blocked": True,
    "training_reload_blocked": True,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class OperatorApprovalEvidenceStatus:
    ok: bool
    source_contract_version: str | None
    source_decision: str | None
    source_report_path: str | None
    operator_approval_verified: bool
    source_transition_candidate: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuntimeEnvelopeFreezeStatus:
    ok: bool
    freeze_required: bool
    frozen: bool
    freeze_token_match: bool
    runtime_envelope: str
    execution_mode: str
    market_type: str
    base_url: str
    auto_trade_on_signal: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    max_open_orders: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FinalRiskCapVerificationStatus:
    ok: bool
    required: bool
    verified: bool
    capital_cap_usd: float
    order_notional_cap_usd: float
    max_daily_loss_usd: float
    max_daily_trades_cap: int
    kill_switch_enabled: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperTransitionCandidateReviewDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_transition_candidate_review: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    operator_approval_evidence_verified: bool
    sandbox_runtime_envelope_frozen: bool
    paper_risk_cap_final_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    operator_approval_evidence: dict[str, Any]
    runtime_envelope_freeze: dict[str, Any]
    final_risk_cap_verification: dict[str, Any]
    source_30b_snapshot: dict[str, Any]

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


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def latest_30b_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [item for item in reports.glob("4B436630B_paper_transition_operator_approval_gate_decision_*.json") if item.is_file()]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def evaluate_operator_approval_evidence(source_30b_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> OperatorApprovalEvidenceStatus:
    source_contract = str(source_30b_snapshot.get("contract_version") or "") or None
    source_decision = str(source_30b_snapshot.get("decision") or "") or None
    operator_ok = bool(source_30b_snapshot.get("operator_approval_verified", False))
    transition_candidate = bool(source_30b_snapshot.get("approved_for_paper_transition_candidate", False))
    reasons: list[str] = []
    if source_contract != SOURCE_30B_CONTRACT_VERSION:
        reasons.append("SOURCE_30B_CONTRACT_VERSION_MISMATCH")
    if source_decision != SOURCE_30B_READY_DECISION:
        reasons.append("SOURCE_30B_OPERATOR_APPROVAL_READY_DECISION_REQUIRED")
    if not operator_ok:
        reasons.append("SOURCE_30B_OPERATOR_APPROVAL_NOT_VERIFIED")
    if not transition_candidate:
        reasons.append("SOURCE_30B_TRANSITION_CANDIDATE_NOT_MARKED")
    if bool(source_30b_snapshot.get("approved_for_paper_candidate", False)):
        reasons.append("SOURCE_30B_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if bool(source_30b_snapshot.get("approved_for_live_real", False)):
        reasons.append("SOURCE_30B_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if bool(source_30b_snapshot.get("trading_action_performed", False)) or bool(source_30b_snapshot.get("order_actions_performed", False)):
        reasons.append("SOURCE_30B_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    ok = source_contract == SOURCE_30B_CONTRACT_VERSION and source_decision == SOURCE_30B_READY_DECISION and operator_ok and transition_candidate and not any("UNEXPECTEDLY" in reason for reason in reasons)
    return OperatorApprovalEvidenceStatus(
        ok=ok,
        source_contract_version=source_contract,
        source_decision=source_decision,
        source_report_path=source_report_path,
        operator_approval_verified=operator_ok,
        source_transition_candidate=transition_candidate,
        reason_codes=reasons or ["OPERATOR_APPROVAL_EVIDENCE_VERIFIED_FROM_30B"],
    )


def evaluate_runtime_envelope_freeze(settings: Any, source_30b_snapshot: Mapping[str, Any], *, supplied_freeze_token: str | None = None) -> RuntimeEnvelopeFreezeStatus:
    envelope = _mapping(source_30b_snapshot.get("sandbox_runtime_envelope"))
    freeze_required = bool(_setting(settings, "paper_transition_runtime_envelope_freeze_required", True))
    frozen = bool(_setting(settings, "paper_transition_runtime_envelope_frozen", False))
    expected_phrase = str(_setting(settings, "paper_transition_runtime_envelope_freeze_phrase", "FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE") or "").strip()
    configured_token = str(_setting(settings, "paper_transition_runtime_envelope_freeze_token", "") or "").strip()
    supplied = str(supplied_freeze_token or configured_token or "").strip()
    token_match = bool(expected_phrase) and supplied == expected_phrase
    runtime_envelope = str(envelope.get("runtime_envelope") or _setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    execution_mode = str(envelope.get("execution_mode") or _setting(settings, "execution_mode", "dry_run") or "").strip().lower()
    market_type = str(envelope.get("market_type") or _setting(settings, "market_type", "spot_demo") or "").strip().lower()
    base_url = str(envelope.get("base_url") or _setting(settings, "base_url", "") or "").strip().lower()
    auto_trade = bool(envelope.get("auto_trade_on_signal", _setting(settings, "auto_trade_on_signal", False)))
    live_armed = bool(envelope.get("live_trading_armed", _setting(settings, "live_trading_armed", False)))
    live_real_double_confirm = bool(envelope.get("live_real_double_confirm", _setting(settings, "live_real_double_confirm", False)))
    max_open_orders = _int(envelope.get("max_open_orders", _setting(settings, "paper_transition_max_open_orders", 1)), 1)
    source_envelope_ok = bool(source_30b_snapshot.get("sandbox_runtime_envelope_verified", False))
    reasons: list[str] = []
    if not source_envelope_ok:
        reasons.append("SOURCE_30B_SANDBOX_RUNTIME_ENVELOPE_NOT_VERIFIED")
    if not freeze_required:
        reasons.append("RUNTIME_ENVELOPE_FREEZE_MUST_REMAIN_REQUIRED")
    if not frozen:
        reasons.append("RUNTIME_ENVELOPE_NOT_FROZEN_BY_OPERATOR")
    if not token_match:
        reasons.append("RUNTIME_ENVELOPE_FREEZE_TOKEN_MISMATCH")
    if runtime_envelope != "sandbox_only":
        reasons.append("RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if execution_mode == "live_real":
        reasons.append("RUNTIME_ENVELOPE_EXECUTION_MODE_LIVE_REAL_BLOCKED")
    if market_type not in {"spot_demo", "spot_testnet"}:
        reasons.append("RUNTIME_ENVELOPE_MARKET_TYPE_NOT_SANDBOX")
    if not (execution_mode == "dry_run" or "demo" in base_url or "testnet" in base_url):
        reasons.append("RUNTIME_ENVELOPE_BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    if auto_trade:
        reasons.append("RUNTIME_ENVELOPE_AUTO_TRADE_UNEXPECTEDLY_ENABLED")
    if live_armed:
        reasons.append("RUNTIME_ENVELOPE_LIVE_TRADING_ARMED_UNEXPECTEDLY_ENABLED")
    if live_real_double_confirm:
        reasons.append("RUNTIME_ENVELOPE_LIVE_REAL_DOUBLE_CONFIRM_UNEXPECTEDLY_ENABLED")
    if max_open_orders != 1:
        reasons.append("RUNTIME_ENVELOPE_MAX_OPEN_ORDERS_MUST_EQUAL_ONE")
    ok = not reasons
    return RuntimeEnvelopeFreezeStatus(
        ok=ok,
        freeze_required=freeze_required,
        frozen=frozen,
        freeze_token_match=token_match,
        runtime_envelope=runtime_envelope,
        execution_mode=execution_mode,
        market_type=market_type,
        base_url=base_url,
        auto_trade_on_signal=auto_trade,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_real_double_confirm,
        max_open_orders=max_open_orders,
        reason_codes=reasons or ["SANDBOX_RUNTIME_ENVELOPE_FROZEN_AND_VERIFIED"],
    )


def evaluate_final_risk_cap_verification(settings: Any, source_30b_snapshot: Mapping[str, Any]) -> FinalRiskCapVerificationStatus:
    preflight = _mapping(source_30b_snapshot.get("paper_preflight_snapshot"))
    risk_limits = _mapping(preflight.get("risk_limits")) or _mapping(_mapping(preflight.get("snapshot")).get("risk_limits"))
    required = bool(_setting(settings, "paper_transition_final_risk_cap_verification_required", True))
    verified = bool(_setting(settings, "paper_transition_final_risk_cap_verified", False))
    capital_cap = _float(risk_limits.get("capital_cap_usd", _setting(settings, "paper_transition_capital_cap_usd", 100.0)), 100.0)
    order_cap = _float(risk_limits.get("order_notional_cap_usd", _setting(settings, "paper_order_notional_cap_usd", 25.0)), 25.0)
    max_daily_loss = _float(risk_limits.get("max_daily_loss_usd", _setting(settings, "paper_max_daily_loss_usd", 5.0)), 5.0)
    max_daily_trades = _int(risk_limits.get("max_daily_trades_cap", _setting(settings, "paper_max_daily_trades_cap", 5)), 5)
    kill_enabled = bool(risk_limits.get("kill_switch_enabled", _setting(settings, "paper_kill_switch_enabled", True)))
    reasons: list[str] = []
    if not required:
        reasons.append("FINAL_RISK_CAP_VERIFICATION_MUST_REMAIN_REQUIRED")
    if not verified:
        reasons.append("FINAL_RISK_CAP_NOT_OPERATOR_VERIFIED")
    if capital_cap <= 0:
        reasons.append("FINAL_RISK_CAPITAL_CAP_NOT_POSITIVE")
    if order_cap <= 0:
        reasons.append("FINAL_RISK_ORDER_CAP_NOT_POSITIVE")
    if order_cap > capital_cap:
        reasons.append("FINAL_RISK_ORDER_CAP_EXCEEDS_CAPITAL_CAP")
    if max_daily_loss <= 0:
        reasons.append("FINAL_RISK_DAILY_LOSS_CAP_NOT_POSITIVE")
    if max_daily_loss > capital_cap:
        reasons.append("FINAL_RISK_DAILY_LOSS_CAP_EXCEEDS_CAPITAL_CAP")
    if max_daily_trades <= 0:
        reasons.append("FINAL_RISK_DAILY_TRADES_CAP_NOT_POSITIVE")
    if not kill_enabled:
        reasons.append("FINAL_RISK_KILL_SWITCH_NOT_ENABLED")
    ok = not reasons
    return FinalRiskCapVerificationStatus(
        ok=ok,
        required=required,
        verified=verified,
        capital_cap_usd=capital_cap,
        order_notional_cap_usd=order_cap,
        max_daily_loss_usd=max_daily_loss,
        max_daily_trades_cap=max_daily_trades,
        kill_switch_enabled=kill_enabled,
        reason_codes=reasons or ["FINAL_PAPER_RISK_CAP_VERIFIED"],
    )


def evaluate_paper_transition_candidate_review(
    settings: Any,
    source_30b_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    supplied_freeze_token: str | None = None,
) -> PaperTransitionCandidateReviewDecision:
    operator = evaluate_operator_approval_evidence(source_30b_snapshot, source_report_path=source_report_path)
    freeze = evaluate_runtime_envelope_freeze(settings, source_30b_snapshot, supplied_freeze_token=supplied_freeze_token)
    risk = evaluate_final_risk_cap_verification(settings, source_30b_snapshot)
    no_paper_enablement = not bool(source_30b_snapshot.get("approved_for_paper_candidate", False)) and not bool(source_30b_snapshot.get("paper_live_order_enablement_present", False))
    no_live_real = not bool(source_30b_snapshot.get("approved_for_live_real", False))
    no_orders = not bool(source_30b_snapshot.get("trading_action_performed", False)) and not bool(source_30b_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    reasons.extend(operator.reason_codes)
    reasons.extend(freeze.reason_codes)
    reasons.extend(risk.reason_codes)
    if not no_paper_enablement:
        reasons.append("PAPER_ORDER_ENABLEMENT_UNEXPECTEDLY_PRESENT")
    if not no_live_real:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not no_orders:
        reasons.append("ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    reasons.append("PAPER_ORDER_ENABLEMENT_STILL_BLOCKED")
    reasons.append("LIVE_REAL_HARD_BLOCK_VERIFIED")
    review_ready = operator.ok and freeze.ok and risk.ok and no_paper_enablement and no_live_real and no_orders
    if review_ready:
        decision = READY_DECISION
    elif "SOURCE_30B_OPERATOR_APPROVAL_NOT_VERIFIED" in reasons or "SOURCE_30B_TRANSITION_CANDIDATE_NOT_MARKED" in reasons:
        decision = OPERATOR_EVIDENCE_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    return PaperTransitionCandidateReviewDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_transition_candidate_review=review_ready,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        operator_approval_evidence_verified=operator.ok,
        sandbox_runtime_envelope_frozen=freeze.ok,
        paper_risk_cap_final_verified=risk.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        operator_approval_evidence=operator.to_dict(),
        runtime_envelope_freeze=freeze.to_dict(),
        final_risk_cap_verification=risk.to_dict(),
        source_30b_snapshot=dict(source_30b_snapshot),
    )


def build_paper_transition_candidate_review_snapshot(
    settings: Any,
    source_30b_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    supplied_freeze_token: str | None = None,
) -> dict[str, Any]:
    decision = evaluate_paper_transition_candidate_review(
        settings,
        source_30b_snapshot,
        source_report_path=source_report_path,
        supplied_freeze_token=supplied_freeze_token,
    )
    payload = decision.to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "operator_approval_evidence_gate": True,
        "sandbox_runtime_envelope_freeze_gate": True,
        "paper_risk_cap_final_verification_gate": True,
        "still_no_paper_order_enablement_gate": True,
        "no_live_real_enforcement": True,
    })
    return payload


def build_from_latest_report(
    settings: Any,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    supplied_freeze_token: str | None = None,
) -> dict[str, Any]:
    source_path = latest_30b_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    return build_paper_transition_candidate_review_snapshot(
        settings,
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
        supplied_freeze_token=supplied_freeze_token,
    )


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} Paper Transition Candidate Review")
    lines.append("")
    lines.append("This report reviews operator approval evidence, freezes the sandbox runtime envelope, performs final paper risk-cap verification, and keeps paper order enablement blocked.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_transition_candidate_review",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "operator_approval_evidence_verified",
        "sandbox_runtime_envelope_frozen",
        "paper_risk_cap_final_verified",
        "paper_order_enablement_still_blocked",
        "trading_action_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Reason codes")
    lines.append("")
    for reason in _sequence(payload.get("reason_codes")):
        lines.append(f"- `{reason}`")
    lines.append("")
    return "\n".join(lines)


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\n")
    return json_path, md_path
