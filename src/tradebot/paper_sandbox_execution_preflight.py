
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

CONTRACT_VERSION = "4B.4.3.6.6.30M"
SOURCE_30L_CONTRACT_VERSION = "4B.4.3.6.6.30L"
SOURCE_30L_READY_DECISION = "PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_READY_PAPER_CANDIDATE_UNLOCKED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
REPORT_TYPE = "paper_sandbox_execution_preflight_order_envelope_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630M_paper_sandbox_execution_preflight"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
ORDER_ENVELOPE_DEFAULT_NAME = "4B436630M_order_envelope_preflight.json"

READY_DECISION = "PAPER_SANDBOX_EXECUTION_PREFLIGHT_READY_ORDER_ENVELOPE_BUILT_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOURCE_30L_REQUIRED_DECISION = "PAPER_SANDBOX_EXECUTION_PREFLIGHT_30L_CANDIDATE_UNLOCK_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
AUTHORIZATION_REQUIRED_DECISION = "PAPER_SANDBOX_EXECUTION_PREFLIGHT_AUTHORIZATION_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SANDBOX_EXECUTION_PREFLIGHT_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

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
class Source30LCandidateUnlockStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    candidate_unlock_gate: bool
    explicit_candidate_unlock: bool
    sandbox_preflight: bool
    paper_sandbox_candidate: bool
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
class DryRunAuthorizationStatus:
    ok: bool
    required: bool
    operator_id: str
    authorization_phrase: str
    authorization_token_matches_phrase: bool
    authorization_issued: bool
    authorization_issued_at_ms: int
    authorization_ttl_sec: int
    authorization_expires_at_ms: int
    authorization_expired: bool
    dry_run_authorization_verified: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OrderEnvelopeStatus:
    ok: bool
    required: bool
    envelope_built: bool
    envelope_written: bool
    envelope_path: str
    envelope: dict[str, Any]
    symbol: str
    side: str
    order_type: str
    quote_notional_usd: float
    order_notional_cap_usd: float
    capital_cap_usd: float
    max_daily_loss_usd: float
    max_daily_trades_cap: int
    max_open_orders: int
    execution_mode: str
    runtime_envelope: str
    market_type: str
    base_url: str
    network_submit_allowed: bool
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
class PaperSandboxExecutionPreflightDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_execution_preflight: bool
    approved_for_30l_candidate_unlock_consumption: bool
    approved_for_paper_sandbox_dry_run_authorization: bool
    approved_for_order_envelope_build: bool
    approved_for_no_exchange_submit_verification: bool
    approved_for_no_live_real_verification: bool
    approved_for_paper_sandbox_candidate: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30l_candidate_unlock_verified: bool
    dry_run_authorization_verified: bool
    order_envelope_built: bool
    order_envelope_written: bool
    no_exchange_submit_verified: bool
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
    source_30l: dict[str, Any]
    dry_run_authorization: dict[str, Any]
    order_envelope: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30l_snapshot: dict[str, Any]

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


def latest_30l_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630L_paper_sandbox_candidate_unlock_gate_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def default_order_envelope_path(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path:
    return Path(reports_dir) / ORDER_ENVELOPE_DEFAULT_NAME


def evaluate_source_30l_candidate_unlock(source_30l_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30LCandidateUnlockStatus:
    contract = str(source_30l_snapshot.get("contract_version") or "") or None
    decision = str(source_30l_snapshot.get("decision") or "") or None
    candidate_gate = bool(source_30l_snapshot.get("approved_for_paper_sandbox_candidate_unlock_gate", False))
    explicit_unlock = bool(source_30l_snapshot.get("approved_for_explicit_paper_candidate_unlock", False))
    sandbox_preflight = bool(source_30l_snapshot.get("approved_for_sandbox_only_order_enablement_preflight", False))
    sandbox_candidate = bool(source_30l_snapshot.get("approved_for_paper_sandbox_candidate", False))
    dry_execution = bool(source_30l_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_submit = bool(source_30l_snapshot.get("approved_for_exchange_submit", False))
    paper_candidate = bool(source_30l_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30l_snapshot.get("approved_for_live_real", False))
    order_blocked = bool(source_30l_snapshot.get("paper_order_enablement_still_blocked", False))
    exchange_performed = bool(source_30l_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30l_snapshot.get("trading_action_performed", False))
    order_actions = bool(source_30l_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if contract != SOURCE_30L_CONTRACT_VERSION:
        reasons.append("SOURCE_30L_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30L_READY_DECISION:
        reasons.append("SOURCE_30L_READY_CANDIDATE_UNLOCK_DECISION_REQUIRED")
    if not candidate_gate:
        reasons.append("SOURCE_30L_CANDIDATE_UNLOCK_GATE_NOT_APPROVED")
    if not explicit_unlock:
        reasons.append("SOURCE_30L_EXPLICIT_CANDIDATE_UNLOCK_NOT_VERIFIED")
    if not sandbox_preflight:
        reasons.append("SOURCE_30L_SANDBOX_PREFLIGHT_NOT_VERIFIED")
    if not sandbox_candidate or not paper_candidate:
        reasons.append("SOURCE_30L_PAPER_SANDBOX_CANDIDATE_NOT_APPROVED")
    if dry_execution:
        reasons.append("SOURCE_30L_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
    if exchange_submit or exchange_performed:
        reasons.append("SOURCE_30L_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if live_real:
        reasons.append("SOURCE_30L_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not order_blocked:
        reasons.append("SOURCE_30L_ORDER_ENABLEMENT_NOT_STILL_BLOCKED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30L_ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30LCandidateUnlockStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        candidate_unlock_gate=candidate_gate,
        explicit_candidate_unlock=explicit_unlock,
        sandbox_preflight=sandbox_preflight,
        paper_sandbox_candidate=sandbox_candidate,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_submit,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_order_enablement_still_blocked=order_blocked,
        exchange_submit_performed=exchange_performed,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30L_CANDIDATE_ONLY_UNLOCK_VERIFIED"],
    )


def evaluate_dry_run_authorization(
    settings: Any,
    *,
    operator_id: str | None = None,
    authorization_token: str | None = None,
    issue_dry_run_authorization: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> DryRunAuthorizationStatus:
    required = bool(_setting(settings, "paper_sandbox_execution_preflight_authorization_required", True))
    phrase = str(_setting(settings, "paper_sandbox_execution_preflight_authorization_phrase", "AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT") or "AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT")
    resolved_operator_id = str(operator_id if operator_id is not None else _setting(settings, "paper_sandbox_execution_preflight_operator_id", "") or "").strip()
    resolved_token = str(authorization_token if authorization_token is not None else _setting(settings, "paper_sandbox_execution_preflight_authorization_token", "") or "").strip()
    resolved_ttl = int(ttl_sec if ttl_sec is not None else _setting(settings, "paper_sandbox_execution_preflight_authorization_ttl_sec", 900) or 900)
    current_ms = int(now_ms if now_ms is not None else _now_ms())
    configured_issued = bool(_setting(settings, "paper_sandbox_execution_preflight_authorization_issued", False))
    issued = bool(issue_dry_run_authorization or configured_issued)
    issued_at = int(current_ms if issue_dry_run_authorization else _setting(settings, "paper_sandbox_execution_preflight_authorization_issued_at_ms", 0) or 0)
    expires_at = issued_at + max(resolved_ttl, 0) * 1000 if issued_at > 0 else 0
    expired = bool(issued and expires_at > 0 and current_ms > expires_at)
    token_ok = resolved_token == phrase
    reasons: list[str] = []
    if not required:
        reasons.append("DRY_RUN_AUTHORIZATION_MUST_REMAIN_REQUIRED")
    if not resolved_operator_id:
        reasons.append("DRY_RUN_AUTHORIZATION_OPERATOR_ID_REQUIRED")
    if not issued:
        reasons.append("DRY_RUN_AUTHORIZATION_NOT_ISSUED")
    if not token_ok:
        reasons.append("DRY_RUN_AUTHORIZATION_TOKEN_MISMATCH")
    if resolved_ttl <= 0:
        reasons.append("DRY_RUN_AUTHORIZATION_TTL_INVALID")
    if expired:
        reasons.append("DRY_RUN_AUTHORIZATION_EXPIRED")
    ok = required and bool(resolved_operator_id) and issued and token_ok and resolved_ttl > 0 and not expired
    return DryRunAuthorizationStatus(
        ok=ok,
        required=required,
        operator_id=resolved_operator_id,
        authorization_phrase=phrase,
        authorization_token_matches_phrase=token_ok,
        authorization_issued=issued,
        authorization_issued_at_ms=issued_at,
        authorization_ttl_sec=resolved_ttl,
        authorization_expires_at_ms=expires_at,
        authorization_expired=expired,
        dry_run_authorization_verified=ok,
        reason_codes=reasons or ["PAPER_SANDBOX_DRY_RUN_AUTHORIZATION_VERIFIED"],
    )


def build_order_envelope(settings: Any, source_30l_snapshot: Mapping[str, Any], *, source_report_path: str | None, now_ms: int | None = None) -> dict[str, Any]:
    timestamp_ms = int(now_ms if now_ms is not None else _now_ms())
    preflight = _mapping(source_30l_snapshot.get("sandbox_order_enablement_preflight"))
    symbol = str(_setting(settings, "symbol", "ETHUSDT") or "ETHUSDT").upper()
    side = str(_setting(settings, "paper_sandbox_execution_preflight_test_side", "BUY") or "BUY").upper()
    order_type = str(_setting(settings, "paper_sandbox_execution_preflight_order_type", "MARKET") or "MARKET").upper()
    quote_notional = _float(_setting(settings, "order_notional_usd", preflight.get("order_notional_usd", 25.0)), 25.0)
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", preflight.get("order_notional_cap_usd", 25.0)), 25.0)
    capital_cap = _float(_setting(settings, "paper_transition_capital_cap_usd", preflight.get("capital_cap_usd", 100.0)), 100.0)
    max_loss = _float(_setting(settings, "paper_max_daily_loss_usd", preflight.get("max_daily_loss_usd", 5.0)), 5.0)
    max_trades = _int(_setting(settings, "paper_max_daily_trades_cap", preflight.get("max_daily_trades_cap", 5)), 5)
    max_open = _int(_setting(settings, "paper_transition_max_open_orders", preflight.get("max_open_orders", 1)), 1)
    return {
        "envelope_id": f"order-envelope-4B436630M-{timestamp_ms}",
        "contract_version": CONTRACT_VERSION,
        "event_type": "paper_sandbox_execution_preflight_order_envelope_no_submit",
        "generated_at_utc": utc_now_iso(),
        "source_30l_report_path": source_report_path,
        "source_30l_decision": source_30l_snapshot.get("decision"),
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quote_notional_usd": quote_notional,
        "order_notional_cap_usd": order_cap,
        "capital_cap_usd": capital_cap,
        "max_daily_loss_usd": max_loss,
        "max_daily_trades_cap": max_trades,
        "max_open_orders": max_open,
        "execution_mode": str(_setting(settings, "execution_mode", "dry_run") or "dry_run").lower(),
        "runtime_envelope": str(_setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "sandbox_only").lower(),
        "market_type": str(_setting(settings, "market_type", "spot_demo") or "spot_demo").lower(),
        "base_url": str(_setting(settings, "base_url", "") or "").lower(),
        "paper_sandbox_candidate": True,
        "paper_sandbox_dry_run_execution_authorized": True,
        "paper_sandbox_dry_run_execution_performed": False,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
    }


def evaluate_order_envelope(
    settings: Any,
    source_30l_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None,
    envelope_path: str | os.PathLike[str],
    build_allowed: bool,
    write_envelope: bool = False,
    now_ms: int | None = None,
) -> OrderEnvelopeStatus:
    required = bool(_setting(settings, "paper_sandbox_execution_preflight_order_envelope_required", True))
    envelope = build_order_envelope(settings, source_30l_snapshot, source_report_path=source_report_path, now_ms=now_ms)
    execution_mode = str(envelope.get("execution_mode") or "").lower()
    runtime_envelope = str(envelope.get("runtime_envelope") or "").lower()
    market_type = str(envelope.get("market_type") or "").lower()
    base_url = str(envelope.get("base_url") or "").lower()
    quote_notional = _float(envelope.get("quote_notional_usd"), 0.0)
    order_cap = _float(envelope.get("order_notional_cap_usd"), 0.0)
    capital_cap = _float(envelope.get("capital_cap_usd"), 0.0)
    max_loss = _float(envelope.get("max_daily_loss_usd"), 0.0)
    max_trades = _int(envelope.get("max_daily_trades_cap"), 0)
    max_open = _int(envelope.get("max_open_orders"), 0)
    reasons: list[str] = []
    if not required:
        reasons.append("ORDER_ENVELOPE_BUILD_MUST_REMAIN_REQUIRED")
    if execution_mode != "dry_run":
        reasons.append("ORDER_ENVELOPE_EXECUTION_MODE_NOT_DRY_RUN")
    if runtime_envelope != "sandbox_only":
        reasons.append("ORDER_ENVELOPE_RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    if market_type not in {"spot_demo", "spot_testnet"}:
        reasons.append("ORDER_ENVELOPE_MARKET_TYPE_NOT_SANDBOX")
    if not ("demo" in base_url or "testnet" in base_url or execution_mode == "dry_run"):
        reasons.append("ORDER_ENVELOPE_BASE_URL_NOT_SANDBOX_OR_DRY_RUN")
    if quote_notional <= 0 or order_cap <= 0 or capital_cap <= 0 or max_loss <= 0 or max_trades <= 0 or max_open <= 0:
        reasons.append("ORDER_ENVELOPE_RISK_CAPS_NOT_POSITIVE")
    if quote_notional > order_cap:
        reasons.append("ORDER_ENVELOPE_NOTIONAL_EXCEEDS_ORDER_CAP")
    if order_cap > capital_cap:
        reasons.append("ORDER_ENVELOPE_ORDER_CAP_EXCEEDS_CAPITAL_CAP")
    if bool(envelope.get("submitted_to_exchange")) or bool(envelope.get("exchange_submit_performed")) or bool(envelope.get("network_submit_attempted")):
        reasons.append("ORDER_ENVELOPE_UNEXPECTED_EXCHANGE_SUBMIT")
    envelope_built = required and build_allowed and not reasons
    envelope_written = False
    if envelope_built and write_envelope:
        write_json_atomic(envelope_path, envelope)
        envelope_written = True
    return OrderEnvelopeStatus(
        ok=envelope_built,
        required=required,
        envelope_built=envelope_built,
        envelope_written=envelope_written,
        envelope_path=Path(envelope_path).as_posix(),
        envelope=envelope if envelope_built else {},
        symbol=str(envelope.get("symbol") or ""),
        side=str(envelope.get("side") or ""),
        order_type=str(envelope.get("order_type") or ""),
        quote_notional_usd=quote_notional,
        order_notional_cap_usd=order_cap,
        capital_cap_usd=capital_cap,
        max_daily_loss_usd=max_loss,
        max_daily_trades_cap=max_trades,
        max_open_orders=max_open,
        execution_mode=execution_mode,
        runtime_envelope=runtime_envelope,
        market_type=market_type,
        base_url=base_url,
        network_submit_allowed=False,
        reason_codes=reasons or ["ORDER_ENVELOPE_BUILT_INTERNAL_ONLY_NO_SUBMIT"],
    )


def evaluate_no_exchange_submit(settings: Any, source_30l_snapshot: Mapping[str, Any]) -> NoExchangeSubmitStatus:
    required = bool(_setting(settings, "paper_sandbox_execution_preflight_no_exchange_submit_required", True))
    approved = bool(source_30l_snapshot.get("approved_for_exchange_submit", False))
    exchange_performed = bool(source_30l_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30l_snapshot.get("trading_action_performed", False)) or bool(source_30l_snapshot.get("order_actions_performed", False))
    order_id_present = bool(source_30l_snapshot.get("exchange_order_id_present", False))
    client_id_present = bool(source_30l_snapshot.get("exchange_client_order_id_present", False))
    reasons: list[str] = []
    if not required:
        reasons.append("EXECUTION_PREFLIGHT_NO_EXCHANGE_SUBMIT_MUST_REMAIN_REQUIRED")
    if approved or exchange_performed:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED_OR_PERFORMED")
    if trading_action:
        reasons.append("ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    if order_id_present:
        reasons.append("EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if client_id_present:
        reasons.append("EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return NoExchangeSubmitStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=trading_action,
        exchange_order_id_present=order_id_present,
        exchange_client_order_id_present=client_id_present,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED_EXECUTION_PREFLIGHT"],
    )


def evaluate_no_live_real(settings: Any, source_30l_snapshot: Mapping[str, Any]) -> NoLiveRealStatus:
    required = bool(_setting(settings, "paper_sandbox_execution_preflight_no_live_real_required", True))
    approved_live_real = bool(source_30l_snapshot.get("approved_for_live_real", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    exchange_performed = bool(source_30l_snapshot.get("exchange_submit_performed", False))
    reasons: list[str] = []
    if not required:
        reasons.append("EXECUTION_PREFLIGHT_NO_LIVE_REAL_MUST_REMAIN_REQUIRED")
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
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_EXECUTION_PREFLIGHT"],
    )


def build_paper_sandbox_execution_preflight_snapshot(
    settings: Any,
    source_30l_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    authorization_token: str | None = None,
    issue_dry_run_authorization: bool = False,
    ttl_sec: int | None = None,
    envelope_path: str | os.PathLike[str] | None = None,
    write_envelope: bool = False,
    now_ms: int | None = None,
) -> dict[str, Any]:
    if not bool(_setting(settings, "paper_sandbox_execution_preflight_enabled", True)):
        source = evaluate_source_30l_candidate_unlock(source_30l_snapshot, source_report_path=source_report_path)
        return {**RISK_FLAGS, "contract_version": CONTRACT_VERSION, "ok": True, "decision": NOT_READY_DECISION, "source_30l": source.to_dict(), "reason_codes": ["EXECUTION_PREFLIGHT_DISABLED"]}
    source = evaluate_source_30l_candidate_unlock(source_30l_snapshot, source_report_path=source_report_path)
    authorization = evaluate_dry_run_authorization(
        settings,
        operator_id=operator_id,
        authorization_token=authorization_token,
        issue_dry_run_authorization=issue_dry_run_authorization,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )
    no_submit = evaluate_no_exchange_submit(settings, source_30l_snapshot)
    no_live = evaluate_no_live_real(settings, source_30l_snapshot)
    resolved_envelope_path = Path(envelope_path) if envelope_path is not None else Path(_setting(settings, "paper_sandbox_execution_preflight_order_envelope_path", "") or default_order_envelope_path(DEFAULT_REPORTS_DIR))
    envelope = evaluate_order_envelope(
        settings,
        source_30l_snapshot,
        source_report_path=source_report_path,
        envelope_path=resolved_envelope_path,
        build_allowed=source.ok and authorization.ok and no_submit.ok and no_live.ok,
        write_envelope=write_envelope,
        now_ms=now_ms,
    )
    reasons = [*source.reason_codes, *authorization.reason_codes, *envelope.reason_codes, *no_submit.reason_codes, *no_live.reason_codes]
    reasons.extend(["ORDER_ENVELOPE_BUILD_NO_EXCHANGE_SUBMIT", "NO_EXCHANGE_SUBMIT_VERIFIED", "NO_LIVE_REAL_VERIFIED", "PAPER_EXECUTION_STILL_BLOCKED_UNTIL_NEXT_GATE"])
    ready = source.ok and authorization.ok and envelope.ok and no_submit.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30L_REQUIRED_DECISION
    elif not authorization.ok:
        decision = AUTHORIZATION_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = PaperSandboxExecutionPreflightDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_execution_preflight=ready,
        approved_for_30l_candidate_unlock_consumption=source.ok,
        approved_for_paper_sandbox_dry_run_authorization=authorization.ok,
        approved_for_order_envelope_build=envelope.ok,
        approved_for_no_exchange_submit_verification=no_submit.ok,
        approved_for_no_live_real_verification=no_live.ok,
        approved_for_paper_sandbox_candidate=source.paper_sandbox_candidate,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_candidate=source.approved_for_paper_candidate,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30l_candidate_unlock_verified=source.ok,
        dry_run_authorization_verified=authorization.ok,
        order_envelope_built=envelope.envelope_built,
        order_envelope_written=envelope.envelope_written,
        no_exchange_submit_verified=no_submit.ok,
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
        source_30l=source.to_dict(),
        dry_run_authorization=authorization.to_dict(),
        order_envelope=envelope.to_dict(),
        no_exchange_submit=no_submit.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30l_snapshot=dict(source_30l_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30l_candidate_unlock_gate": True,
        "paper_sandbox_dry_run_authorization_gate": True,
        "order_envelope_build_gate": True,
        "no_exchange_submit_gate": True,
        "no_live_real_gate": True,
        "paper_sandbox_execution_preflight": True,
        "paper_sandbox_candidate_only": source.paper_sandbox_candidate,
        "paper_execution_still_requires_next_explicit_gate": True,
        "exchange_submit_still_requires_next_explicit_gate": True,
    })
    return payload


def build_from_latest_30l_ready_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    authorization_token: str | None = None,
    issue_dry_run_authorization: bool = False,
    ttl_sec: int | None = None,
    envelope_path: str | os.PathLike[str] | None = None,
    write_envelope: bool = False,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source_path = latest_30l_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    resolved_settings = settings or Settings()
    resolved_envelope = Path(envelope_path) if envelope_path is not None else Path(_setting(resolved_settings, "paper_sandbox_execution_preflight_order_envelope_path", "") or default_order_envelope_path(reports_dir))
    return build_paper_sandbox_execution_preflight_snapshot(
        resolved_settings,
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
        operator_id=operator_id,
        authorization_token=authorization_token,
        issue_dry_run_authorization=issue_dry_run_authorization,
        ttl_sec=ttl_sec,
        envelope_path=resolved_envelope,
        write_envelope=write_envelope,
        now_ms=now_ms,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == AUTHORIZATION_REQUIRED_DECISION:
        return "authorization_required"
    if decision == SOURCE_30L_REQUIRED_DECISION:
        return "30l_required"
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
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Execution Preflight")
    lines.append("")
    lines.append("This report consumes the 30L-H2 accepted candidate-only unlock, verifies dry-run authorization, builds an internal order envelope, and keeps exchange submit and live-real blocked.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_execution_preflight",
        "approved_for_30l_candidate_unlock_consumption",
        "approved_for_paper_sandbox_dry_run_authorization",
        "approved_for_order_envelope_build",
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
        "source_30l_candidate_unlock_verified",
        "dry_run_authorization_verified",
        "order_envelope_built",
        "order_envelope_written",
        "no_exchange_submit_verified",
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
