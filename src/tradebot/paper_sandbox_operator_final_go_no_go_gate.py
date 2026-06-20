from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30K"
SOURCE_30J_CONTRACT_VERSION = "4B.4.3.6.6.30J"
SOURCE_30J_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_READY_MISMATCH_ZERO_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED"
REPORT_TYPE = "paper_sandbox_operator_final_go_no_go_gate_no_live_real"
REPORT_PREFIX = "4B436630K_paper_sandbox_operator_final_go_no_go_gate"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_READY_PAPER_CANDIDATE_STILL_BLOCKED_NO_LIVE_REAL"
SOURCE_30J_REQUIRED_DECISION = "PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_30J_RECONCILIATION_PROOF_REQUIRED_NO_LIVE_REAL"
OPERATOR_APPROVAL_REQUIRED_DECISION = "PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_OPERATOR_APPROVAL_REQUIRED_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_NOT_READY_NO_LIVE_REAL"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
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
class Source30JStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    reconciliation_proof: bool
    ledger_consumed: bool
    mismatch_zero: bool
    sqlite_mirror: bool
    no_exchange_submit: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    mismatch_count: int
    exchange_submit_performed: bool
    trading_action_performed: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorFinalApprovalStatus:
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
    final_paper_sandbox_approval_verified: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class KillSwitchCapsChecklistStatus:
    ok: bool
    kill_switch_required: bool
    kill_switch_enabled: bool
    kill_switch_confirmed_by_operator: bool
    caps_required: bool
    caps_confirmed_by_operator: bool
    runtime_envelope: str
    allowed_market_types: list[str]
    order_notional_cap_usd: float
    transition_capital_cap_usd: float
    max_daily_loss_usd: float
    max_daily_trades_cap: int
    max_open_orders: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperCandidateStillBlockedStatus:
    ok: bool
    required: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_live_order_enablement_present: bool
    order_actions_performed: bool
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
class OperatorFinalGoNoGoDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_operator_final_go_no_go_gate: bool
    approved_for_operator_final_paper_sandbox_approval: bool
    approved_for_kill_switch_caps_checklist: bool
    approved_for_paper_sandbox_go_no_go_candidate: bool
    approved_for_no_live_real_verification: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30j_reconciliation_proof_verified: bool
    operator_final_approval_verified: bool
    kill_switch_caps_checklist_verified: bool
    paper_candidate_still_blocked_verified: bool
    no_live_real_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    order_actions_performed: bool
    exchange_submit_performed: bool
    reason_codes: list[str]
    source_30j: dict[str, Any]
    operator_final_approval: dict[str, Any]
    kill_switch_caps_checklist: dict[str, Any]
    paper_candidate_still_blocked: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30j_snapshot: dict[str, Any]

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


def latest_30j_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger_proof_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def evaluate_source_30j_reconciliation_proof(source_30j_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30JStatus:
    contract = str(source_30j_snapshot.get("contract_version") or "") or None
    decision = str(source_30j_snapshot.get("decision") or "") or None
    proof = bool(source_30j_snapshot.get("approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof", False))
    ledger = bool(source_30j_snapshot.get("approved_for_30i_simulated_fill_ledger_consumption", False)) or bool(source_30j_snapshot.get("simulated_fill_ledger_consumed", False))
    mismatch_count = _int(source_30j_snapshot.get("mismatch_count", 999), 999)
    mismatch_zero = bool(source_30j_snapshot.get("approved_for_mismatch_zero_proof", False)) or bool(source_30j_snapshot.get("reconciliation_mismatch_zero_verified", False))
    sqlite = bool(source_30j_snapshot.get("approved_for_sqlite_audit_mirror", False)) or bool(source_30j_snapshot.get("sqlite_audit_mirror_verified", False))
    no_submit = bool(source_30j_snapshot.get("approved_for_no_exchange_submit_verification", False)) or bool(source_30j_snapshot.get("no_exchange_submit_verified", False))
    dry_execution = bool(source_30j_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_approved = bool(source_30j_snapshot.get("approved_for_exchange_submit", False))
    transition_candidate = bool(source_30j_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30j_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30j_snapshot.get("approved_for_live_real", False))
    exchange_performed = bool(source_30j_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30j_snapshot.get("trading_action_performed", False))
    order_actions = bool(source_30j_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if contract != SOURCE_30J_CONTRACT_VERSION:
        reasons.append("SOURCE_30J_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30J_READY_DECISION:
        reasons.append("SOURCE_30J_READY_RECONCILIATION_DECISION_REQUIRED")
    if not proof:
        reasons.append("SOURCE_30J_RECONCILIATION_PROOF_NOT_APPROVED")
    if not ledger:
        reasons.append("SOURCE_30J_LEDGER_CONSUMPTION_NOT_VERIFIED")
    if mismatch_count != 0 or not mismatch_zero:
        reasons.append("SOURCE_30J_MISMATCH_ZERO_REQUIRED")
    if not sqlite:
        reasons.append("SOURCE_30J_SQLITE_MIRROR_NOT_VERIFIED")
    if not no_submit or exchange_approved or exchange_performed:
        reasons.append("SOURCE_30J_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if dry_execution:
        reasons.append("SOURCE_30J_PAPER_EXECUTION_UNEXPECTEDLY_ENABLED")
    if transition_candidate:
        reasons.append("SOURCE_30J_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("SOURCE_30J_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30J_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30J_ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30JStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        reconciliation_proof=proof,
        ledger_consumed=ledger,
        mismatch_zero=(mismatch_count == 0 and mismatch_zero),
        sqlite_mirror=sqlite,
        no_exchange_submit=no_submit and not exchange_approved and not exchange_performed,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_approved,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        mismatch_count=mismatch_count,
        exchange_submit_performed=exchange_performed,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30J_RECONCILIATION_PROOF_VERIFIED"],
    )


def evaluate_operator_final_approval(
    settings: Any,
    *,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_final_approval: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> OperatorFinalApprovalStatus:
    required = bool(_setting(settings, "paper_sandbox_operator_final_approval_required", True))
    phrase = str(_setting(settings, "paper_sandbox_operator_final_approval_phrase", "APPROVE_PAPER_SANDBOX_GO_NO_GO") or "APPROVE_PAPER_SANDBOX_GO_NO_GO")
    resolved_operator_id = str(operator_id if operator_id is not None else _setting(settings, "paper_sandbox_operator_final_approval_operator_id", "") or "").strip()
    resolved_token = str(approval_token if approval_token is not None else _setting(settings, "paper_sandbox_operator_final_approval_token", "") or "").strip()
    resolved_ttl = int(ttl_sec if ttl_sec is not None else _setting(settings, "paper_sandbox_operator_final_approval_ttl_sec", 900) or 900)
    current_ms = int(now_ms if now_ms is not None else _now_ms())
    configured_issued = bool(_setting(settings, "paper_sandbox_operator_final_approval_issued", False))
    issued = bool(issue_final_approval or configured_issued)
    issued_at = int(current_ms if issue_final_approval else _setting(settings, "paper_sandbox_operator_final_approval_issued_at_ms", 0) or 0)
    expires_at = issued_at + max(resolved_ttl, 0) * 1000 if issued_at > 0 else 0
    expired = bool(issued and expires_at > 0 and current_ms > expires_at)
    token_ok = resolved_token == phrase
    reasons: list[str] = []
    if not required:
        reasons.append("OPERATOR_FINAL_APPROVAL_MUST_REMAIN_REQUIRED")
    if not resolved_operator_id:
        reasons.append("OPERATOR_FINAL_APPROVAL_OPERATOR_ID_REQUIRED")
    if not issued:
        reasons.append("OPERATOR_FINAL_APPROVAL_NOT_ISSUED")
    if not token_ok:
        reasons.append("OPERATOR_FINAL_APPROVAL_TOKEN_MISMATCH")
    if resolved_ttl <= 0:
        reasons.append("OPERATOR_FINAL_APPROVAL_TTL_INVALID")
    if expired:
        reasons.append("OPERATOR_FINAL_APPROVAL_EXPIRED")
    ok = required and bool(resolved_operator_id) and issued and token_ok and resolved_ttl > 0 and not expired
    return OperatorFinalApprovalStatus(
        ok=ok,
        required=required,
        operator_id=resolved_operator_id,
        approval_phrase=phrase,
        approval_token_matches_phrase=token_ok,
        approval_issued=issued,
        approval_issued_at_ms=issued_at,
        approval_ttl_sec=resolved_ttl,
        approval_expires_at_ms=expires_at,
        approval_expired=expired,
        final_paper_sandbox_approval_verified=ok,
        reason_codes=reasons or ["OPERATOR_FINAL_PAPER_SANDBOX_APPROVAL_VERIFIED"],
    )


def evaluate_kill_switch_caps_checklist(
    settings: Any,
    *,
    confirm_kill_switch: bool = False,
    confirm_caps: bool = False,
) -> KillSwitchCapsChecklistStatus:
    kill_required = bool(_setting(settings, "paper_sandbox_operator_kill_switch_check_required", True))
    kill_enabled = bool(_setting(settings, "paper_kill_switch_enabled", True))
    caps_required = bool(_setting(settings, "paper_sandbox_operator_caps_check_required", True))
    runtime_envelope = str(_setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    allowed_market_types = [item.strip() for item in str(_setting(settings, "paper_sandbox_allowed_market_types", "spot_demo,spot_testnet") or "").split(",") if item.strip()]
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", 25.0), 25.0)
    capital_cap = _float(_setting(settings, "paper_transition_capital_cap_usd", 100.0), 100.0)
    daily_loss = _float(_setting(settings, "paper_max_daily_loss_usd", 5.0), 5.0)
    max_trades = _int(_setting(settings, "paper_max_daily_trades_cap", 5), 5)
    max_open_orders = _int(_setting(settings, "paper_transition_max_open_orders", 1), 1)
    kill_confirmed = bool(confirm_kill_switch or _setting(settings, "paper_sandbox_operator_kill_switch_confirmed", False))
    caps_confirmed = bool(confirm_caps or _setting(settings, "paper_sandbox_operator_caps_confirmed", False))
    reasons: list[str] = []
    if not kill_required:
        reasons.append("KILL_SWITCH_CHECK_MUST_REMAIN_REQUIRED")
    if not kill_enabled:
        reasons.append("PAPER_KILL_SWITCH_NOT_ENABLED")
    if not kill_confirmed:
        reasons.append("OPERATOR_KILL_SWITCH_CONFIRMATION_REQUIRED")
    if not caps_required:
        reasons.append("CAPS_CHECK_MUST_REMAIN_REQUIRED")
    if not caps_confirmed:
        reasons.append("OPERATOR_CAPS_CONFIRMATION_REQUIRED")
    if runtime_envelope != "sandbox_only":
        reasons.append("RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if not set(allowed_market_types).intersection({"spot_demo", "spot_testnet"}):
        reasons.append("SANDBOX_MARKET_TYPE_ALLOWLIST_MISSING")
    if order_cap <= 0 or capital_cap <= 0 or daily_loss <= 0 or max_trades <= 0 or max_open_orders <= 0:
        reasons.append("PAPER_RISK_CAPS_NOT_POSITIVE")
    if order_cap > capital_cap:
        reasons.append("ORDER_NOTIONAL_CAP_EXCEEDS_CAPITAL_CAP")
    ok = not reasons
    return KillSwitchCapsChecklistStatus(
        ok=ok,
        kill_switch_required=kill_required,
        kill_switch_enabled=kill_enabled,
        kill_switch_confirmed_by_operator=kill_confirmed,
        caps_required=caps_required,
        caps_confirmed_by_operator=caps_confirmed,
        runtime_envelope=runtime_envelope,
        allowed_market_types=allowed_market_types,
        order_notional_cap_usd=order_cap,
        transition_capital_cap_usd=capital_cap,
        max_daily_loss_usd=daily_loss,
        max_daily_trades_cap=max_trades,
        max_open_orders=max_open_orders,
        reason_codes=reasons or ["KILL_SWITCH_AND_RISK_CAPS_CHECKLIST_VERIFIED"],
    )


def evaluate_paper_candidate_still_blocked(settings: Any, source_30j_snapshot: Mapping[str, Any]) -> PaperCandidateStillBlockedStatus:
    required = bool(_setting(settings, "paper_sandbox_operator_paper_candidate_still_blocked_required", True))
    dry_execution = bool(source_30j_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_approved = bool(source_30j_snapshot.get("approved_for_exchange_submit", False))
    transition_candidate = bool(source_30j_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30j_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30j_snapshot.get("approved_for_live_real", False))
    paper_enablement = bool(source_30j_snapshot.get("paper_live_order_enablement_present", False))
    order_actions = bool(source_30j_snapshot.get("trading_action_performed", False)) or bool(source_30j_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_CANDIDATE_BLOCK_UNTIL_EXPLICIT_APPROVAL_MUST_REMAIN_REQUIRED")
    if dry_execution:
        reasons.append("PAPER_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
    if exchange_approved:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED")
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
    return PaperCandidateStillBlockedStatus(
        ok=required and not reasons,
        required=required,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_approved,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_live_order_enablement_present=paper_enablement,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["PAPER_CANDIDATE_STILL_BLOCKED_UNTIL_EXPLICIT_APPROVAL"],
    )


def evaluate_no_live_real(settings: Any, source_30j_snapshot: Mapping[str, Any]) -> NoLiveRealStatus:
    required = bool(_setting(settings, "paper_sandbox_operator_no_live_real_required", True))
    approved_live_real = bool(source_30j_snapshot.get("approved_for_live_real", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    exchange_performed = bool(source_30j_snapshot.get("exchange_submit_performed", False))
    reasons: list[str] = []
    if not required:
        reasons.append("NO_LIVE_REAL_GATE_MUST_REMAIN_REQUIRED")
    if approved_live_real or live_armed or live_confirm:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_ENABLED_OR_ARMED")
    if exchange_performed:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_PERFORMED")
    return NoLiveRealStatus(
        ok=required and not reasons,
        required=required,
        approved_for_live_real=approved_live_real,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_confirm,
        exchange_submit_performed=exchange_performed,
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_OPERATOR_FINAL_GATE"],
    )


def build_paper_sandbox_operator_final_go_no_go_snapshot(
    settings: Any,
    source_30j_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_final_approval: bool = False,
    confirm_kill_switch: bool = False,
    confirm_caps: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    if not bool(_setting(settings, "paper_sandbox_operator_final_go_no_go_gate_enabled", True)):
        source = evaluate_source_30j_reconciliation_proof({}, source_report_path=source_report_path)
    else:
        source = evaluate_source_30j_reconciliation_proof(source_30j_snapshot, source_report_path=source_report_path)
    approval = evaluate_operator_final_approval(
        settings,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_final_approval=issue_final_approval,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )
    checklist = evaluate_kill_switch_caps_checklist(settings, confirm_kill_switch=confirm_kill_switch, confirm_caps=confirm_caps)
    candidate_block = evaluate_paper_candidate_still_blocked(settings, source_30j_snapshot)
    no_live = evaluate_no_live_real(settings, source_30j_snapshot)
    reasons = [*source.reason_codes, *approval.reason_codes, *checklist.reason_codes, *candidate_block.reason_codes, *no_live.reason_codes]
    reasons.extend(["PAPER_CANDIDATE_REMAINS_BLOCKED_UNTIL_NEXT_EXPLICIT_APPROVAL", "NO_LIVE_REAL_VERIFIED"])
    ready = source.ok and approval.ok and checklist.ok and candidate_block.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30J_REQUIRED_DECISION
    elif not approval.ok:
        decision = OPERATOR_APPROVAL_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = OperatorFinalGoNoGoDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_operator_final_go_no_go_gate=ready,
        approved_for_operator_final_paper_sandbox_approval=approval.ok,
        approved_for_kill_switch_caps_checklist=checklist.ok,
        approved_for_paper_sandbox_go_no_go_candidate=ready,
        approved_for_no_live_real_verification=no_live.ok,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30j_reconciliation_proof_verified=source.ok,
        operator_final_approval_verified=approval.ok,
        kill_switch_caps_checklist_verified=checklist.ok,
        paper_candidate_still_blocked_verified=candidate_block.ok,
        no_live_real_verified=no_live.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        order_actions_performed=False,
        exchange_submit_performed=False,
        reason_codes=reasons,
        source_30j=source.to_dict(),
        operator_final_approval=approval.to_dict(),
        kill_switch_caps_checklist=checklist.to_dict(),
        paper_candidate_still_blocked=candidate_block.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30j_snapshot=dict(source_30j_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "paper_sandbox_operator_final_go_no_go_gate": True,
        "source_30j_reconciliation_proof_gate": True,
        "operator_final_paper_sandbox_approval_gate": True,
        "kill_switch_caps_checklist_gate": True,
        "paper_candidate_still_blocked_until_next_explicit_approval_gate": True,
        "no_live_real_gate": True,
    })
    return payload


def build_from_latest_30j_ready_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_final_approval: bool = False,
    confirm_kill_switch: bool = False,
    confirm_caps: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source_path = latest_30j_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    return build_paper_sandbox_operator_final_go_no_go_snapshot(
        settings or Settings(),
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_final_approval=issue_final_approval,
        confirm_kill_switch=confirm_kill_switch,
        confirm_caps=confirm_caps,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_30J_REQUIRED_DECISION:
        return "30j_required"
    if decision == OPERATOR_APPROVAL_REQUIRED_DECISION:
        return "operator_required"
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
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Operator Final Go/No-Go Gate")
    lines.append("")
    lines.append("This report consumes the 30J reconciliation proof, verifies operator final approval plus kill-switch/caps checklist, and keeps paper candidate, exchange submit, and live-real blocked.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_operator_final_go_no_go_gate",
        "approved_for_operator_final_paper_sandbox_approval",
        "approved_for_kill_switch_caps_checklist",
        "approved_for_paper_sandbox_go_no_go_candidate",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_exchange_submit",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "paper_order_enablement_still_blocked",
        "trading_action_performed",
        "exchange_submit_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Gate checks")
    for key in (
        "source_30j_reconciliation_proof_verified",
        "operator_final_approval_verified",
        "kill_switch_caps_checklist_verified",
        "paper_candidate_still_blocked_verified",
        "no_live_real_verified",
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
