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

CONTRACT_VERSION = "4B.4.3.6.6.30L"
SOURCE_30K_CONTRACT_VERSION = "4B.4.3.6.6.30K"
SOURCE_30K_READY_DECISION = "PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_READY_PAPER_CANDIDATE_STILL_BLOCKED_NO_LIVE_REAL"
REPORT_TYPE = "paper_sandbox_candidate_unlock_gate_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630L_paper_sandbox_candidate_unlock_gate"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_READY_PAPER_CANDIDATE_UNLOCKED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOURCE_30K_REQUIRED_DECISION = "PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_30K_READY_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
UNLOCK_REQUIRED_DECISION = "PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_EXPLICIT_UNLOCK_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
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
class Source30KStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    operator_final_gate: bool
    operator_final_approval: bool
    kill_switch_caps_checklist: bool
    go_no_go_candidate: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_order_enablement_still_blocked: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExplicitCandidateUnlockStatus:
    ok: bool
    required: bool
    operator_id: str
    unlock_phrase: str
    unlock_token_matches_phrase: bool
    unlock_issued: bool
    unlock_issued_at_ms: int
    unlock_ttl_sec: int
    unlock_expires_at_ms: int
    unlock_expired: bool
    explicit_candidate_unlock_verified: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SandboxOrderEnablementPreflightStatus:
    ok: bool
    required: bool
    execution_mode: str
    runtime_envelope: str
    market_type: str
    base_url: str
    allowed_market_types: list[str]
    sandbox_required: bool
    auto_trade_on_signal: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    kill_switch_enabled: bool
    order_notional_usd: float
    order_notional_cap_usd: float
    capital_cap_usd: float
    max_daily_loss_usd: float
    max_daily_trades_cap: int
    max_open_orders: int
    network_submit_allowed: bool
    order_enablement_still_blocked: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoExchangeSubmitYetStatus:
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
class PaperSandboxCandidateUnlockDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_candidate_unlock_gate: bool
    approved_for_explicit_paper_candidate_unlock: bool
    approved_for_sandbox_only_order_enablement_preflight: bool
    approved_for_paper_sandbox_candidate: bool
    approved_for_no_exchange_submit_verification: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30k_go_no_go_verified: bool
    explicit_candidate_unlock_verified: bool
    sandbox_only_order_enablement_preflight_verified: bool
    no_exchange_submit_yet_verified: bool
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
    source_30k: dict[str, Any]
    explicit_candidate_unlock: dict[str, Any]
    sandbox_order_enablement_preflight: dict[str, Any]
    no_exchange_submit_yet: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30k_snapshot: dict[str, Any]

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


def latest_30k_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630K_paper_sandbox_operator_final_go_no_go_gate_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def evaluate_source_30k_go_no_go(source_30k_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30KStatus:
    contract = str(source_30k_snapshot.get("contract_version") or "") or None
    decision = str(source_30k_snapshot.get("decision") or "") or None
    final_gate = bool(source_30k_snapshot.get("approved_for_paper_sandbox_operator_final_go_no_go_gate", False))
    approval = bool(source_30k_snapshot.get("approved_for_operator_final_paper_sandbox_approval", False))
    checklist = bool(source_30k_snapshot.get("approved_for_kill_switch_caps_checklist", False))
    go_no_go = bool(source_30k_snapshot.get("approved_for_paper_sandbox_go_no_go_candidate", False))
    dry_execution = bool(source_30k_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_submit = bool(source_30k_snapshot.get("approved_for_exchange_submit", False))
    paper_candidate = bool(source_30k_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30k_snapshot.get("approved_for_live_real", False))
    order_blocked = bool(source_30k_snapshot.get("paper_order_enablement_still_blocked", False))
    exchange_performed = bool(source_30k_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30k_snapshot.get("trading_action_performed", False))
    order_actions = bool(source_30k_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if contract != SOURCE_30K_CONTRACT_VERSION:
        reasons.append("SOURCE_30K_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30K_READY_DECISION:
        reasons.append("SOURCE_30K_READY_GO_NO_GO_DECISION_REQUIRED")
    if not final_gate:
        reasons.append("SOURCE_30K_FINAL_GO_NO_GO_GATE_NOT_APPROVED")
    if not approval:
        reasons.append("SOURCE_30K_OPERATOR_FINAL_APPROVAL_NOT_VERIFIED")
    if not checklist:
        reasons.append("SOURCE_30K_KILL_SWITCH_CAPS_CHECKLIST_NOT_VERIFIED")
    if not go_no_go:
        reasons.append("SOURCE_30K_GO_NO_GO_CANDIDATE_NOT_APPROVED")
    if dry_execution:
        reasons.append("SOURCE_30K_PAPER_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
    if exchange_submit or exchange_performed:
        reasons.append("SOURCE_30K_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if paper_candidate:
        reasons.append("SOURCE_30K_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30K_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not order_blocked:
        reasons.append("SOURCE_30K_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30K_ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30KStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        operator_final_gate=final_gate,
        operator_final_approval=approval,
        kill_switch_caps_checklist=checklist,
        go_no_go_candidate=go_no_go,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_submit,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_order_enablement_still_blocked=order_blocked,
        exchange_submit_performed=exchange_performed,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30K_FINAL_GO_NO_GO_READY_VERIFIED"],
    )


def evaluate_explicit_candidate_unlock(
    settings: Any,
    *,
    operator_id: str | None = None,
    unlock_token: str | None = None,
    issue_candidate_unlock: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> ExplicitCandidateUnlockStatus:
    required = bool(_setting(settings, "paper_sandbox_candidate_unlock_explicit_unlock_required", True))
    phrase = str(_setting(settings, "paper_sandbox_candidate_unlock_phrase", "UNLOCK_PAPER_SANDBOX_CANDIDATE") or "UNLOCK_PAPER_SANDBOX_CANDIDATE")
    resolved_operator_id = str(operator_id if operator_id is not None else _setting(settings, "paper_sandbox_candidate_unlock_operator_id", "") or "").strip()
    resolved_token = str(unlock_token if unlock_token is not None else _setting(settings, "paper_sandbox_candidate_unlock_token", "") or "").strip()
    resolved_ttl = int(ttl_sec if ttl_sec is not None else _setting(settings, "paper_sandbox_candidate_unlock_ttl_sec", 900) or 900)
    current_ms = int(now_ms if now_ms is not None else _now_ms())
    configured_issued = bool(_setting(settings, "paper_sandbox_candidate_unlock_issued", False))
    issued = bool(issue_candidate_unlock or configured_issued)
    issued_at = int(current_ms if issue_candidate_unlock else _setting(settings, "paper_sandbox_candidate_unlock_issued_at_ms", 0) or 0)
    expires_at = issued_at + max(resolved_ttl, 0) * 1000 if issued_at > 0 else 0
    expired = bool(issued and expires_at > 0 and current_ms > expires_at)
    token_ok = resolved_token == phrase
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_CANDIDATE_UNLOCK_MUST_REMAIN_REQUIRED")
    if not resolved_operator_id:
        reasons.append("PAPER_CANDIDATE_UNLOCK_OPERATOR_ID_REQUIRED")
    if not issued:
        reasons.append("PAPER_CANDIDATE_UNLOCK_NOT_ISSUED")
    if not token_ok:
        reasons.append("PAPER_CANDIDATE_UNLOCK_TOKEN_MISMATCH")
    if resolved_ttl <= 0:
        reasons.append("PAPER_CANDIDATE_UNLOCK_TTL_INVALID")
    if expired:
        reasons.append("PAPER_CANDIDATE_UNLOCK_EXPIRED")
    ok = required and bool(resolved_operator_id) and issued and token_ok and resolved_ttl > 0 and not expired
    return ExplicitCandidateUnlockStatus(
        ok=ok,
        required=required,
        operator_id=resolved_operator_id,
        unlock_phrase=phrase,
        unlock_token_matches_phrase=token_ok,
        unlock_issued=issued,
        unlock_issued_at_ms=issued_at,
        unlock_ttl_sec=resolved_ttl,
        unlock_expires_at_ms=expires_at,
        unlock_expired=expired,
        explicit_candidate_unlock_verified=ok,
        reason_codes=reasons or ["EXPLICIT_PAPER_SANDBOX_CANDIDATE_UNLOCK_VERIFIED"],
    )


def evaluate_sandbox_only_order_enablement_preflight(settings: Any) -> SandboxOrderEnablementPreflightStatus:
    required = bool(_setting(settings, "paper_sandbox_candidate_unlock_sandbox_only_preflight_required", True))
    execution_mode = str(_setting(settings, "execution_mode", "dry_run") or "").strip().lower()
    runtime_envelope = str(_setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    market_type = str(_setting(settings, "market_type", "spot_demo") or "").strip().lower()
    base_url = str(_setting(settings, "base_url", "") or "").strip().lower()
    allowed = [item.strip().lower() for item in str(_setting(settings, "paper_sandbox_allowed_market_types", "spot_demo,spot_testnet") or "").split(",") if item.strip()]
    sandbox_required = bool(_setting(settings, "paper_exchange_sandbox_required", True))
    auto_trade = bool(_setting(settings, "auto_trade_on_signal", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    kill_switch = bool(_setting(settings, "paper_kill_switch_enabled", True))
    order_notional = _float(_setting(settings, "order_notional_usd", 25.0), 25.0)
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", 25.0), 25.0)
    capital_cap = _float(_setting(settings, "paper_transition_capital_cap_usd", 100.0), 100.0)
    daily_loss = _float(_setting(settings, "paper_max_daily_loss_usd", 5.0), 5.0)
    max_trades = _int(_setting(settings, "paper_max_daily_trades_cap", 5), 5)
    max_open_orders = _int(_setting(settings, "paper_transition_max_open_orders", 1), 1)
    order_enablement_still_blocked = bool(_setting(settings, "paper_sandbox_candidate_unlock_order_enablement_still_blocked_required", True))
    reasons: list[str] = []
    if not required:
        reasons.append("SANDBOX_ORDER_ENABLEMENT_PREFLIGHT_MUST_REMAIN_REQUIRED")
    if not sandbox_required:
        reasons.append("PAPER_EXCHANGE_SANDBOX_REQUIREMENT_DISABLED")
    if execution_mode != "dry_run":
        reasons.append("EXECUTION_MODE_NOT_DRY_RUN")
    if runtime_envelope != "sandbox_only":
        reasons.append("RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if market_type not in {"spot_demo", "spot_testnet"} or (allowed and market_type not in set(allowed)):
        reasons.append("MARKET_TYPE_NOT_ALLOWED_SANDBOX")
    if not ("demo" in base_url or "testnet" in base_url or execution_mode == "dry_run"):
        reasons.append("BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    if auto_trade:
        reasons.append("AUTO_TRADE_UNEXPECTEDLY_ENABLED")
    if live_armed or live_confirm:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_ARMED")
    if not kill_switch:
        reasons.append("PAPER_KILL_SWITCH_NOT_ENABLED")
    if order_notional <= 0 or order_cap <= 0 or capital_cap <= 0 or daily_loss <= 0 or max_trades <= 0 or max_open_orders <= 0:
        reasons.append("PAPER_SANDBOX_CAPS_NOT_POSITIVE")
    if order_notional > order_cap:
        reasons.append("ORDER_NOTIONAL_EXCEEDS_PAPER_ORDER_CAP")
    if order_cap > capital_cap:
        reasons.append("ORDER_CAP_EXCEEDS_CAPITAL_CAP")
    if not order_enablement_still_blocked:
        reasons.append("ORDER_ENABLEMENT_STILL_BLOCKED_REQUIREMENT_DISABLED")
    ok = required and not reasons
    return SandboxOrderEnablementPreflightStatus(
        ok=ok,
        required=required,
        execution_mode=execution_mode,
        runtime_envelope=runtime_envelope,
        market_type=market_type,
        base_url=base_url,
        allowed_market_types=allowed,
        sandbox_required=sandbox_required,
        auto_trade_on_signal=auto_trade,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_confirm,
        kill_switch_enabled=kill_switch,
        order_notional_usd=order_notional,
        order_notional_cap_usd=order_cap,
        capital_cap_usd=capital_cap,
        max_daily_loss_usd=daily_loss,
        max_daily_trades_cap=max_trades,
        max_open_orders=max_open_orders,
        network_submit_allowed=False,
        order_enablement_still_blocked=order_enablement_still_blocked,
        reason_codes=reasons or ["SANDBOX_ONLY_ORDER_ENABLEMENT_PREFLIGHT_VERIFIED_NO_SUBMIT"],
    )


def evaluate_no_exchange_submit_yet(settings: Any, source_30k_snapshot: Mapping[str, Any]) -> NoExchangeSubmitYetStatus:
    required = bool(_setting(settings, "paper_sandbox_candidate_unlock_no_exchange_submit_required", True))
    approved = bool(source_30k_snapshot.get("approved_for_exchange_submit", False))
    exchange_performed = bool(source_30k_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30k_snapshot.get("trading_action_performed", False)) or bool(source_30k_snapshot.get("order_actions_performed", False))
    exchange_order_id_present = bool(source_30k_snapshot.get("exchange_order_id_present", False))
    exchange_client_order_id_present = bool(source_30k_snapshot.get("exchange_client_order_id_present", False))
    reasons: list[str] = []
    if not required:
        reasons.append("NO_EXCHANGE_SUBMIT_YET_GATE_MUST_REMAIN_REQUIRED")
    if approved or exchange_performed:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED_OR_PERFORMED")
    if trading_action:
        reasons.append("ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    if exchange_order_id_present:
        reasons.append("EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if exchange_client_order_id_present:
        reasons.append("EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return NoExchangeSubmitYetStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=trading_action,
        exchange_order_id_present=exchange_order_id_present,
        exchange_client_order_id_present=exchange_client_order_id_present,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_YET_VERIFIED"],
    )


def evaluate_no_live_real(settings: Any, source_30k_snapshot: Mapping[str, Any]) -> NoLiveRealStatus:
    required = bool(_setting(settings, "paper_sandbox_candidate_unlock_no_live_real_required", True))
    approved_live_real = bool(source_30k_snapshot.get("approved_for_live_real", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    exchange_performed = bool(source_30k_snapshot.get("exchange_submit_performed", False))
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
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_CANDIDATE_UNLOCK_GATE"],
    )


def build_paper_sandbox_candidate_unlock_snapshot(
    settings: Any,
    source_30k_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    unlock_token: str | None = None,
    issue_candidate_unlock: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30k_go_no_go(source_30k_snapshot, source_report_path=source_report_path)
    unlock = evaluate_explicit_candidate_unlock(
        settings,
        operator_id=operator_id,
        unlock_token=unlock_token,
        issue_candidate_unlock=issue_candidate_unlock,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )
    preflight = evaluate_sandbox_only_order_enablement_preflight(settings)
    no_submit = evaluate_no_exchange_submit_yet(settings, source_30k_snapshot)
    no_live = evaluate_no_live_real(settings, source_30k_snapshot)
    reasons = [*source.reason_codes, *unlock.reason_codes, *preflight.reason_codes, *no_submit.reason_codes, *no_live.reason_codes]
    reasons.extend(["NO_EXCHANGE_SUBMIT_YET", "NO_LIVE_REAL_VERIFIED", "ORDER_ENABLEMENT_STILL_BLOCKED_UNTIL_NEXT_EXECUTION_GATE"])
    ready = source.ok and unlock.ok and preflight.ok and no_submit.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30K_REQUIRED_DECISION
    elif not unlock.ok:
        decision = UNLOCK_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = PaperSandboxCandidateUnlockDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_candidate_unlock_gate=ready,
        approved_for_explicit_paper_candidate_unlock=unlock.ok,
        approved_for_sandbox_only_order_enablement_preflight=preflight.ok,
        approved_for_paper_sandbox_candidate=ready,
        approved_for_no_exchange_submit_verification=no_submit.ok,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_candidate=ready,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30k_go_no_go_verified=source.ok,
        explicit_candidate_unlock_verified=unlock.ok,
        sandbox_only_order_enablement_preflight_verified=preflight.ok,
        no_exchange_submit_yet_verified=no_submit.ok,
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
        source_30k=source.to_dict(),
        explicit_candidate_unlock=unlock.to_dict(),
        sandbox_order_enablement_preflight=preflight.to_dict(),
        no_exchange_submit_yet=no_submit.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30k_snapshot=dict(source_30k_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30k_go_no_go_gate": True,
        "explicit_paper_candidate_unlock_gate": True,
        "sandbox_only_order_enablement_preflight_gate": True,
        "no_exchange_submit_yet_gate": True,
        "no_live_real_gate": True,
        "paper_candidate_unlocked_as_candidate_only": ready,
        "order_enablement_preflight_passed": preflight.ok,
        "exchange_submit_still_requires_next_explicit_gate": True,
    })
    return payload


def build_from_latest_30k_ready_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    unlock_token: str | None = None,
    issue_candidate_unlock: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source_path = latest_30k_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    return build_paper_sandbox_candidate_unlock_snapshot(
        settings or Settings(),
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
        operator_id=operator_id,
        unlock_token=unlock_token,
        issue_candidate_unlock=issue_candidate_unlock,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_30K_REQUIRED_DECISION:
        return "30k_required"
    if decision == UNLOCK_REQUIRED_DECISION:
        return "unlock_required"
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
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Candidate Unlock Gate")
    lines.append("")
    lines.append("This report consumes the 30K final go/no-go gate, verifies explicit paper candidate unlock, runs sandbox-only order enablement preflight, and keeps exchange submit and live-real blocked.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_candidate_unlock_gate",
        "approved_for_explicit_paper_candidate_unlock",
        "approved_for_sandbox_only_order_enablement_preflight",
        "approved_for_paper_sandbox_candidate",
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
        "source_30k_go_no_go_verified",
        "explicit_candidate_unlock_verified",
        "sandbox_only_order_enablement_preflight_verified",
        "no_exchange_submit_yet_verified",
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
