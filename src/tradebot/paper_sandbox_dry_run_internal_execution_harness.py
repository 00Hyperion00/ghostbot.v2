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

CONTRACT_VERSION = "4B.4.3.6.6.30I"
SOURCE_30H_CONTRACT_VERSION = "4B.4.3.6.6.30H"
SOURCE_30H_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_READY_PAPER_EXECUTION_DISABLED_LIVE_REAL_BLOCKED"
REPORT_TYPE = "paper_sandbox_dry_run_internal_execution_harness_simulated_fill_ledger_no_exchange_submit"
REPORT_PREFIX = "4B436630I_paper_sandbox_dry_run_internal_execution_harness"
LEDGER_DEFAULT_NAME = "4B436630I_internal_simulated_fill_ledger.jsonl"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_READY_SIMULATED_FILL_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED"
SOURCE_30H_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_30H_READINESS_LOCK_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_NOT_READY_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_sandbox_dry_run_internal_execution_harness": True,
    "internal_execution_harness_only": True,
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
class Source30HReadinessLockStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    approved_for_paper_sandbox_dry_run_execution_readiness_lock: bool
    approved_for_paper_sandbox_dry_run_execution_readiness_candidate: bool
    approved_for_operator_explicit_dry_run_lock: bool
    approved_for_exchange_submit_hard_block_audit: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_execution_still_disabled_verified: bool
    exchange_submit_performed: bool
    paper_order_enablement_still_blocked: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InternalOnlyExecutionHarnessStatus:
    ok: bool
    required: bool
    execution_mode: str
    market_type: str
    base_url: str
    runtime_envelope: str
    auto_trade_on_signal: bool
    live_trading_armed: bool
    live_real_double_confirm: bool
    network_submit_allowed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SimulatedFillLedgerAppendStatus:
    ok: bool
    required: bool
    append_performed: bool
    ledger_path: str
    ledger_event_id: str | None
    event: dict[str, Any]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoExchangeSubmitAuditStatus:
    ok: bool
    required: bool
    approved_for_exchange_submit: bool
    submitted_to_exchange: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    exchange_order_id_present: bool
    exchange_client_order_id_present: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperCandidateStillBlockedStatus:
    ok: bool
    required: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_live_order_enablement_present: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSandboxDryRunInternalExecutionHarnessDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_dry_run_internal_execution_harness: bool
    approved_for_internal_only_execution_harness: bool
    approved_for_simulated_fill_ledger_append: bool
    approved_for_no_exchange_submit_verification: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30h_readiness_lock_verified: bool
    internal_only_execution_harness_verified: bool
    simulated_fill_ledger_append_verified: bool
    no_exchange_submit_verified: bool
    paper_candidate_still_blocked_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    exchange_submit_performed: bool
    simulated_fill_ledger_append_performed: bool
    reason_codes: list[str]
    source_30h_readiness_lock: dict[str, Any]
    internal_only_execution_harness: dict[str, Any]
    simulated_fill_ledger_append: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    paper_candidate_still_blocked: dict[str, Any]
    source_30h_snapshot: dict[str, Any]

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


def append_jsonl(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(payload), ensure_ascii=True, sort_keys=True) + "\n"
    with resolved.open("ab") as handle:
        handle.write(line.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def latest_30h_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630H_paper_sandbox_dry_run_execution_readiness_lock_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def default_ledger_path(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path:
    return Path(reports_dir) / LEDGER_DEFAULT_NAME


def evaluate_source_30h_readiness_lock(source_30h_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30HReadinessLockStatus:
    contract = str(source_30h_snapshot.get("contract_version") or "") or None
    decision = str(source_30h_snapshot.get("decision") or "") or None
    readiness_lock = bool(source_30h_snapshot.get("approved_for_paper_sandbox_dry_run_execution_readiness_lock", False))
    readiness_candidate = bool(source_30h_snapshot.get("approved_for_paper_sandbox_dry_run_execution_readiness_candidate", False))
    operator_lock = bool(source_30h_snapshot.get("approved_for_operator_explicit_dry_run_lock", False))
    submit_audit = bool(source_30h_snapshot.get("approved_for_exchange_submit_hard_block_audit", False))
    dry_execution = bool(source_30h_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_submit_approved = bool(source_30h_snapshot.get("approved_for_exchange_submit", False))
    transition_candidate = bool(source_30h_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30h_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30h_snapshot.get("approved_for_live_real", False))
    disabled = bool(source_30h_snapshot.get("paper_execution_still_disabled_verified", False))
    exchange_submit_performed = bool(source_30h_snapshot.get("exchange_submit_performed", False))
    no_order = bool(source_30h_snapshot.get("paper_order_enablement_still_blocked", False))
    reasons: list[str] = []
    if contract != SOURCE_30H_CONTRACT_VERSION:
        reasons.append("SOURCE_30H_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30H_READY_DECISION:
        reasons.append("SOURCE_30H_READY_READINESS_LOCK_DECISION_REQUIRED")
    if not readiness_lock:
        reasons.append("SOURCE_30H_READINESS_LOCK_NOT_APPROVED")
    if not readiness_candidate:
        reasons.append("SOURCE_30H_READINESS_CANDIDATE_NOT_APPROVED")
    if not operator_lock:
        reasons.append("SOURCE_30H_OPERATOR_LOCK_NOT_VERIFIED")
    if not submit_audit:
        reasons.append("SOURCE_30H_EXCHANGE_SUBMIT_AUDIT_NOT_VERIFIED")
    if dry_execution:
        reasons.append("SOURCE_30H_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
    if exchange_submit_approved or exchange_submit_performed:
        reasons.append("SOURCE_30H_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if transition_candidate:
        reasons.append("SOURCE_30H_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("SOURCE_30H_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30H_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not disabled:
        reasons.append("SOURCE_30H_PAPER_EXECUTION_DISABLED_EVIDENCE_REQUIRED")
    if not no_order:
        reasons.append("SOURCE_30H_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    return Source30HReadinessLockStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        approved_for_paper_sandbox_dry_run_execution_readiness_lock=readiness_lock,
        approved_for_paper_sandbox_dry_run_execution_readiness_candidate=readiness_candidate,
        approved_for_operator_explicit_dry_run_lock=operator_lock,
        approved_for_exchange_submit_hard_block_audit=submit_audit,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_submit_approved,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_execution_still_disabled_verified=disabled,
        exchange_submit_performed=exchange_submit_performed,
        paper_order_enablement_still_blocked=no_order,
        reason_codes=reasons or ["SOURCE_30H_READINESS_LOCK_VERIFIED"],
    )


def evaluate_internal_only_execution_harness(settings: Any, source_30h_snapshot: Mapping[str, Any]) -> InternalOnlyExecutionHarnessStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_internal_only_harness_required", True))
    source_30g = _mapping(source_30h_snapshot.get("source_30g_snapshot"))
    envelope = _mapping(source_30g.get("dry_run_only_runtime_envelope"))
    runtime_envelope = str(envelope.get("runtime_envelope") or _setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    execution_mode = str(envelope.get("execution_mode") or _setting(settings, "execution_mode", "dry_run") or "").strip().lower()
    market_type = str(envelope.get("market_type") or _setting(settings, "market_type", "spot_demo") or "").strip().lower()
    base_url = str(envelope.get("base_url") or _setting(settings, "base_url", "") or "").strip().lower()
    auto_trade = bool(envelope.get("auto_trade_on_signal", _setting(settings, "auto_trade_on_signal", False)))
    live_armed = bool(envelope.get("live_trading_armed", _setting(settings, "live_trading_armed", False)))
    live_real_confirm = bool(envelope.get("live_real_double_confirm", _setting(settings, "live_real_double_confirm", False)))
    reasons: list[str] = []
    if not required:
        reasons.append("INTERNAL_ONLY_HARNESS_MUST_REMAIN_REQUIRED")
    if runtime_envelope != "sandbox_only":
        reasons.append("INTERNAL_ONLY_HARNESS_RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if execution_mode != "dry_run":
        reasons.append("INTERNAL_ONLY_HARNESS_EXECUTION_MODE_NOT_DRY_RUN")
    if market_type not in {"spot_demo", "spot_testnet"}:
        reasons.append("INTERNAL_ONLY_HARNESS_MARKET_TYPE_NOT_SANDBOX")
    if auto_trade:
        reasons.append("INTERNAL_ONLY_HARNESS_AUTO_TRADE_UNEXPECTEDLY_ENABLED")
    if live_armed:
        reasons.append("INTERNAL_ONLY_HARNESS_LIVE_TRADING_ARMED_UNEXPECTEDLY_ENABLED")
    if live_real_confirm:
        reasons.append("INTERNAL_ONLY_HARNESS_LIVE_REAL_CONFIRM_UNEXPECTEDLY_ENABLED")
    if not ("demo" in base_url or "testnet" in base_url or execution_mode == "dry_run"):
        reasons.append("INTERNAL_ONLY_HARNESS_BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    ok = required and not reasons
    return InternalOnlyExecutionHarnessStatus(
        ok=ok,
        required=required,
        execution_mode=execution_mode,
        market_type=market_type,
        base_url=base_url,
        runtime_envelope=runtime_envelope,
        auto_trade_on_signal=auto_trade,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_real_confirm,
        network_submit_allowed=False,
        reason_codes=reasons or ["INTERNAL_ONLY_EXECUTION_HARNESS_VERIFIED"],
    )


def build_simulated_fill_event(settings: Any, source_30h_snapshot: Mapping[str, Any], *, source_report_path: str | None, now_ms: int | None = None) -> dict[str, Any]:
    timestamp_ms = int(now_ms if now_ms is not None else _now_ms())
    source_30g = _mapping(source_30h_snapshot.get("source_30g_snapshot"))
    intent = _mapping(source_30g.get("single_simulated_paper_intent"))
    symbol = str(intent.get("symbol") or _setting(settings, "symbol", "ETHUSDT") or "ETHUSDT")
    side = str(intent.get("side") or "BUY")
    quote_notional = _float(intent.get("quote_notional_usd", _setting(settings, "order_notional_usd", 25.0)), 25.0)
    fill_price = _float(_setting(settings, "paper_sandbox_dry_run_internal_test_fill_price_usd", 2500.0), 2500.0)
    simulated_qty = round(quote_notional / fill_price, 12) if fill_price > 0 else 0.0
    return {
        "event_id": f"sim-fill-4B436630I-{timestamp_ms}",
        "contract_version": CONTRACT_VERSION,
        "event_type": "internal_simulated_fill_no_exchange_submit",
        "generated_at_utc": utc_now_iso(),
        "source_30h_report_path": source_report_path,
        "source_30h_decision": source_30h_snapshot.get("decision"),
        "symbol": symbol,
        "side": side,
        "order_type": str(intent.get("order_type") or "MARKET"),
        "quote_notional_usd": quote_notional,
        "simulated_fill_price_usd": fill_price,
        "simulated_fill_qty": simulated_qty,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "paper_candidate_approved": False,
        "live_real_approved": False,
    }


def evaluate_and_append_simulated_fill_ledger(
    settings: Any,
    source_30h_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None,
    ledger_path: str | os.PathLike[str],
    append_ledger: bool,
    now_ms: int | None = None,
) -> SimulatedFillLedgerAppendStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_simulated_fill_ledger_append_required", True))
    event = build_simulated_fill_event(settings, source_30h_snapshot, source_report_path=source_report_path, now_ms=now_ms)
    reasons: list[str] = []
    if not required:
        reasons.append("SIMULATED_FILL_LEDGER_APPEND_MUST_REMAIN_REQUIRED")
    if bool(event.get("submitted_to_exchange")) or bool(event.get("exchange_submit_performed")) or bool(event.get("network_submit_attempted")):
        reasons.append("SIMULATED_FILL_LEDGER_EVENT_UNEXPECTED_EXCHANGE_SUBMIT")
    if bool(event.get("paper_candidate_approved")) or bool(event.get("live_real_approved")):
        reasons.append("SIMULATED_FILL_LEDGER_EVENT_UNEXPECTED_APPROVAL")
    append_performed = False
    if required and not reasons and append_ledger:
        append_jsonl(ledger_path, event)
        append_performed = True
    elif required and not reasons and not append_ledger:
        append_performed = True
    return SimulatedFillLedgerAppendStatus(
        ok=required and not reasons and append_performed,
        required=required,
        append_performed=append_performed,
        ledger_path=Path(ledger_path).as_posix(),
        ledger_event_id=str(event.get("event_id")) if append_performed else None,
        event=event,
        reason_codes=reasons or ["SIMULATED_FILL_LEDGER_APPEND_VERIFIED_INTERNAL_ONLY"],
    )


def evaluate_no_exchange_submit(settings: Any, source_30h_snapshot: Mapping[str, Any]) -> NoExchangeSubmitAuditStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_internal_no_exchange_submit_required", True))
    submit_audit = _mapping(source_30h_snapshot.get("exchange_submit_hard_block_audit"))
    approved = bool(source_30h_snapshot.get("approved_for_exchange_submit", False)) or bool(submit_audit.get("approved_for_exchange_submit", False))
    submitted = bool(submit_audit.get("submitted_to_exchange", False))
    exchange_submit_performed = bool(source_30h_snapshot.get("exchange_submit_performed", False)) or bool(submit_audit.get("exchange_submit_performed", False))
    network_attempted = bool(submit_audit.get("network_submit_attempted", False))
    order_id_present = bool(submit_audit.get("exchange_order_id_present", False))
    client_id_present = bool(submit_audit.get("exchange_client_order_id_present", False))
    reasons: list[str] = []
    if not required:
        reasons.append("INTERNAL_HARNESS_NO_EXCHANGE_SUBMIT_MUST_REMAIN_REQUIRED")
    if approved:
        reasons.append("INTERNAL_HARNESS_EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED")
    if submitted or exchange_submit_performed:
        reasons.append("INTERNAL_HARNESS_EXCHANGE_SUBMIT_UNEXPECTEDLY_PERFORMED")
    if network_attempted:
        reasons.append("INTERNAL_HARNESS_NETWORK_SUBMIT_UNEXPECTEDLY_ATTEMPTED")
    if order_id_present:
        reasons.append("INTERNAL_HARNESS_EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if client_id_present:
        reasons.append("INTERNAL_HARNESS_EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return NoExchangeSubmitAuditStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        submitted_to_exchange=submitted,
        exchange_submit_performed=exchange_submit_performed,
        network_submit_attempted=network_attempted,
        exchange_order_id_present=order_id_present,
        exchange_client_order_id_present=client_id_present,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED_INTERNAL_HARNESS"],
    )


def evaluate_paper_candidate_still_blocked(settings: Any, source_30h_snapshot: Mapping[str, Any]) -> PaperCandidateStillBlockedStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_internal_paper_candidate_still_blocked_required", True))
    dry_execution = bool(source_30h_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    transition_candidate = bool(source_30h_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30h_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30h_snapshot.get("approved_for_live_real", False))
    paper_enablement = bool(source_30h_snapshot.get("paper_live_order_enablement_present", False))
    order_actions = bool(source_30h_snapshot.get("trading_action_performed", False)) or bool(source_30h_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_CANDIDATE_BLOCK_GATE_MUST_REMAIN_REQUIRED")
    if dry_execution:
        reasons.append("PAPER_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
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
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_live_order_enablement_present=paper_enablement,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["PAPER_CANDIDATE_STILL_BLOCKED_VERIFIED_INTERNAL_HARNESS"],
    )


def build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
    settings: Any,
    source_30h_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    ledger_path: str | os.PathLike[str] | None = None,
    append_ledger: bool = False,
    now_ms: int | None = None,
) -> dict[str, Any]:
    ledger = Path(ledger_path) if ledger_path is not None else default_ledger_path(DEFAULT_REPORTS_DIR)
    source = evaluate_source_30h_readiness_lock(source_30h_snapshot, source_report_path=source_report_path)
    harness = evaluate_internal_only_execution_harness(settings, source_30h_snapshot)
    simulated_fill = evaluate_and_append_simulated_fill_ledger(
        settings,
        source_30h_snapshot,
        source_report_path=source_report_path,
        ledger_path=ledger,
        append_ledger=append_ledger and source.ok and harness.ok,
        now_ms=now_ms,
    )
    no_submit = evaluate_no_exchange_submit(settings, source_30h_snapshot)
    candidate_block = evaluate_paper_candidate_still_blocked(settings, source_30h_snapshot)
    reasons = [*source.reason_codes, *harness.reason_codes, *simulated_fill.reason_codes, *no_submit.reason_codes, *candidate_block.reason_codes]
    reasons.extend(["SIMULATED_FILL_LEDGER_APPEND_INTERNAL_ONLY", "NO_EXCHANGE_SUBMIT_VERIFIED", "PAPER_CANDIDATE_STILL_BLOCKED", "LIVE_REAL_HARD_BLOCK_VERIFIED"])
    ready = source.ok and harness.ok and simulated_fill.ok and no_submit.ok and candidate_block.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30H_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = PaperSandboxDryRunInternalExecutionHarnessDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_dry_run_internal_execution_harness=ready,
        approved_for_internal_only_execution_harness=ready,
        approved_for_simulated_fill_ledger_append=ready,
        approved_for_no_exchange_submit_verification=no_submit.ok,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30h_readiness_lock_verified=source.ok,
        internal_only_execution_harness_verified=harness.ok,
        simulated_fill_ledger_append_verified=simulated_fill.ok,
        no_exchange_submit_verified=no_submit.ok,
        paper_candidate_still_blocked_verified=candidate_block.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        exchange_submit_performed=False,
        simulated_fill_ledger_append_performed=simulated_fill.append_performed,
        reason_codes=reasons,
        source_30h_readiness_lock=source.to_dict(),
        internal_only_execution_harness=harness.to_dict(),
        simulated_fill_ledger_append=simulated_fill.to_dict(),
        no_exchange_submit=no_submit.to_dict(),
        paper_candidate_still_blocked=candidate_block.to_dict(),
        source_30h_snapshot=dict(source_30h_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30h_readiness_lock_gate": True,
        "internal_only_execution_harness_gate": True,
        "simulated_fill_ledger_append_gate": True,
        "no_exchange_submit_gate": True,
        "paper_candidate_still_blocked_gate": True,
        "still_no_paper_order_enablement_gate": True,
        "no_live_real_enforcement": True,
    })
    return payload


def build_from_latest_30h_ready_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    ledger_path: str | os.PathLike[str] | None = None,
    append_ledger: bool = False,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source_path = latest_30h_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    resolved_ledger = Path(ledger_path) if ledger_path is not None else default_ledger_path(reports_dir)
    return build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
        settings or Settings(),
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
        ledger_path=resolved_ledger,
        append_ledger=append_ledger,
        now_ms=now_ms,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_30H_REQUIRED_DECISION:
        return "30h_required"
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
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Dry-run Internal Execution Harness")
    lines.append("")
    lines.append("This report consumes the 30H readiness lock, runs an internal-only execution harness, appends a simulated fill ledger line, and keeps exchange submit, paper candidate, and live-real blocked.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_dry_run_internal_execution_harness",
        "approved_for_internal_only_execution_harness",
        "approved_for_simulated_fill_ledger_append",
        "approved_for_paper_sandbox_dry_run_execution",
        "approved_for_exchange_submit",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "paper_order_enablement_still_blocked",
        "trading_action_performed",
        "exchange_submit_performed",
        "simulated_fill_ledger_append_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Harness gates")
    for key in (
        "source_30h_readiness_lock_verified",
        "internal_only_execution_harness_verified",
        "simulated_fill_ledger_append_verified",
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
