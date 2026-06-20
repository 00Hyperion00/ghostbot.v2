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

CONTRACT_VERSION = "4B.4.3.6.6.30N"
SOURCE_30M_CONTRACT_VERSION = "4B.4.3.6.6.30M"
SOURCE_30M_READY_DECISION = "PAPER_SANDBOX_EXECUTION_PREFLIGHT_READY_ORDER_ENVELOPE_BUILT_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
REPORT_TYPE = "paper_sandbox_dry_run_execution_gate_internal_simulation_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630N_paper_sandbox_dry_run_execution_gate"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
LEDGER_DEFAULT_NAME = "4B436630N_internal_paper_execution_ledger.jsonl"

READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_READY_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOURCE_30M_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_30M_ORDER_ENVELOPE_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
AUTHORIZATION_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_EXECUTION_AUTHORIZATION_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

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
class Source30MOrderEnvelopeStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    execution_preflight: bool
    candidate_unlock_consumed: bool
    dry_run_authorization: bool
    order_envelope_build: bool
    order_envelope_built: bool
    order_envelope_written: bool
    approved_for_paper_candidate: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    paper_order_enablement_still_blocked: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperDryRunExecutionAuthorizationStatus:
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
    paper_dry_run_execution_authorization_verified: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperExecutionSimulationStatus:
    ok: bool
    required: bool
    execution_simulated: bool
    ledger_appended: bool
    ledger_path: str
    event: dict[str, Any]
    symbol: str
    side: str
    order_type: str
    quote_notional_usd: float
    simulated_fill_price_usd: float
    simulated_fill_qty: float
    simulated_fee_bps: float
    simulated_fee_usd: float
    net_quote_delta_usd: float
    net_base_delta: float
    network_submit_allowed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NoExchangeSubmitStatus:
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
class PaperSandboxDryRunExecutionDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_dry_run_execution_gate: bool
    approved_for_30m_order_envelope_consumption: bool
    approved_for_internal_paper_execution_simulation: bool
    approved_for_paper_execution_ledger_append: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30m_order_envelope_verified: bool
    paper_dry_run_execution_authorization_verified: bool
    internal_paper_execution_simulated: bool
    paper_execution_ledger_appended: bool
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
    source_30m: dict[str, Any]
    paper_dry_run_execution_authorization: dict[str, Any]
    internal_paper_execution_simulation: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30m_snapshot: dict[str, Any]

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


def append_jsonl_atomic(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
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
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed == parsed and abs(parsed) != float("inf") else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def latest_30m_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630M_paper_sandbox_execution_preflight_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def default_ledger_path(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path:
    return Path(reports_dir) / LEDGER_DEFAULT_NAME


def _order_envelope_from_source_or_file(
    settings: Any,
    source_30m_snapshot: Mapping[str, Any],
    reports_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    direct = _mapping(source_30m_snapshot.get("order_envelope"))
    nested = _mapping(_mapping(source_30m_snapshot.get("order_envelope_build")).get("envelope"))
    if direct:
        return dict(direct)
    if nested:
        return dict(nested)
    configured = str(_setting(settings, "paper_sandbox_execution_preflight_order_envelope_path", "") or "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path(reports_dir) / "4B436630M_order_envelope_preflight.json")
    for path in candidates:
        try:
            if path.exists():
                payload = load_json(path)
                if isinstance(payload, dict):
                    return payload
        except OSError:
            continue
    return {}


def evaluate_source_30m_order_envelope(source_30m_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30MOrderEnvelopeStatus:
    contract = str(source_30m_snapshot.get("contract_version") or "") or None
    decision = str(source_30m_snapshot.get("decision") or "") or None
    preflight = bool(source_30m_snapshot.get("approved_for_paper_sandbox_execution_preflight", False))
    consumed_30l = bool(source_30m_snapshot.get("approved_for_30l_candidate_unlock_consumption", False))
    auth = bool(source_30m_snapshot.get("approved_for_paper_sandbox_dry_run_authorization", False))
    envelope_build = bool(source_30m_snapshot.get("approved_for_order_envelope_build", False))
    envelope_built = bool(source_30m_snapshot.get("order_envelope_built", False))
    envelope_written = bool(source_30m_snapshot.get("order_envelope_written", False))
    paper_candidate = bool(source_30m_snapshot.get("approved_for_paper_candidate", False))
    dry_execution = bool(source_30m_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_submit = bool(source_30m_snapshot.get("approved_for_exchange_submit", False))
    live_real = bool(source_30m_snapshot.get("approved_for_live_real", False))
    order_blocked = bool(source_30m_snapshot.get("paper_order_enablement_still_blocked", False))
    exchange_performed = bool(source_30m_snapshot.get("exchange_submit_performed", False))
    trading_action = bool(source_30m_snapshot.get("trading_action_performed", False))
    order_actions = bool(source_30m_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if contract != SOURCE_30M_CONTRACT_VERSION:
        reasons.append("SOURCE_30M_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30M_READY_DECISION:
        reasons.append("SOURCE_30M_READY_ORDER_ENVELOPE_DECISION_REQUIRED")
    if not preflight:
        reasons.append("SOURCE_30M_EXECUTION_PREFLIGHT_NOT_APPROVED")
    if not consumed_30l:
        reasons.append("SOURCE_30M_30L_CONSUMPTION_NOT_VERIFIED")
    if not auth:
        reasons.append("SOURCE_30M_DRY_RUN_AUTHORIZATION_NOT_VERIFIED")
    if not envelope_build or not envelope_built:
        reasons.append("SOURCE_30M_ORDER_ENVELOPE_NOT_BUILT")
    if not envelope_written:
        reasons.append("SOURCE_30M_ORDER_ENVELOPE_NOT_WRITTEN")
    if not paper_candidate:
        reasons.append("SOURCE_30M_PAPER_CANDIDATE_NOT_PRESERVED")
    if dry_execution:
        reasons.append("SOURCE_30M_DRY_RUN_EXECUTION_UNEXPECTEDLY_ALREADY_ENABLED")
    if exchange_submit or exchange_performed:
        reasons.append("SOURCE_30M_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if live_real:
        reasons.append("SOURCE_30M_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not order_blocked:
        reasons.append("SOURCE_30M_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30M_ORDER_OR_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30MOrderEnvelopeStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        execution_preflight=preflight,
        candidate_unlock_consumed=consumed_30l,
        dry_run_authorization=auth,
        order_envelope_build=envelope_build,
        order_envelope_built=envelope_built,
        order_envelope_written=envelope_written,
        approved_for_paper_candidate=paper_candidate,
        approved_for_paper_sandbox_dry_run_execution=dry_execution,
        approved_for_exchange_submit=exchange_submit,
        approved_for_live_real=live_real,
        paper_order_enablement_still_blocked=order_blocked,
        exchange_submit_performed=exchange_performed,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30M_ORDER_ENVELOPE_PREFLIGHT_VERIFIED"],
    )


def evaluate_paper_dry_run_execution_authorization(
    settings: Any,
    *,
    operator_id: str | None = None,
    authorization_token: str | None = None,
    issue_execution_authorization: bool = False,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> PaperDryRunExecutionAuthorizationStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_execution_authorization_required", True))
    phrase = str(_setting(settings, "paper_sandbox_dry_run_execution_authorization_phrase", "AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION") or "AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION")
    resolved_operator_id = str(operator_id if operator_id is not None else _setting(settings, "paper_sandbox_dry_run_execution_operator_id", "") or "").strip()
    resolved_token = str(authorization_token if authorization_token is not None else _setting(settings, "paper_sandbox_dry_run_execution_authorization_token", "") or "").strip()
    resolved_ttl = int(ttl_sec if ttl_sec is not None else _setting(settings, "paper_sandbox_dry_run_execution_authorization_ttl_sec", 900) or 900)
    current_ms = int(now_ms if now_ms is not None else _now_ms())
    configured_issued = bool(_setting(settings, "paper_sandbox_dry_run_execution_authorization_issued", False))
    issued = bool(issue_execution_authorization or configured_issued)
    issued_at = int(current_ms if issue_execution_authorization else _setting(settings, "paper_sandbox_dry_run_execution_authorization_issued_at_ms", 0) or 0)
    expires_at = issued_at + max(resolved_ttl, 0) * 1000 if issued_at > 0 else 0
    expired = bool(issued and expires_at > 0 and current_ms > expires_at)
    token_ok = resolved_token == phrase
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_DRY_RUN_EXECUTION_AUTHORIZATION_MUST_REMAIN_REQUIRED")
    if not resolved_operator_id:
        reasons.append("PAPER_DRY_RUN_EXECUTION_AUTHORIZATION_OPERATOR_ID_REQUIRED")
    if not issued:
        reasons.append("PAPER_DRY_RUN_EXECUTION_AUTHORIZATION_NOT_ISSUED")
    if not token_ok:
        reasons.append("PAPER_DRY_RUN_EXECUTION_AUTHORIZATION_TOKEN_MISMATCH")
    if resolved_ttl <= 0:
        reasons.append("PAPER_DRY_RUN_EXECUTION_AUTHORIZATION_TTL_INVALID")
    if expired:
        reasons.append("PAPER_DRY_RUN_EXECUTION_AUTHORIZATION_EXPIRED")
    ok = required and bool(resolved_operator_id) and issued and token_ok and resolved_ttl > 0 and not expired
    return PaperDryRunExecutionAuthorizationStatus(
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
        paper_dry_run_execution_authorization_verified=ok,
        reason_codes=reasons or ["INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION_AUTHORIZATION_VERIFIED"],
    )


def _asset_pair(symbol: str) -> tuple[str, str]:
    upper = str(symbol or "UNKNOWN").upper()
    for quote in ("USDT", "BUSD", "USDC", "BTC", "ETH", "BNB", "USD"):
        if upper.endswith(quote) and len(upper) > len(quote):
            return upper[: -len(quote)], quote
    return upper, "QUOTE"


def build_execution_event(
    settings: Any,
    source_30m_snapshot: Mapping[str, Any],
    order_envelope: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    current_ms = int(now_ms if now_ms is not None else _now_ms())
    symbol = str(order_envelope.get("symbol") or _setting(settings, "symbol", "ETHUSDT") or "ETHUSDT").upper()
    side = str(order_envelope.get("side") or "BUY").upper()
    order_type = str(order_envelope.get("order_type") or "MARKET").upper()
    quote_notional = _float(order_envelope.get("quote_notional_usd", _setting(settings, "order_notional_usd", 25.0)), 25.0)
    fill_price = _float(_setting(settings, "paper_sandbox_dry_run_execution_simulated_fill_price_usd", 2500.0), 2500.0)
    fee_bps = _float(_setting(settings, "paper_sandbox_dry_run_execution_simulated_fee_bps", 10.0), 10.0)
    fill_qty = quote_notional / fill_price if fill_price > 0 else 0.0
    fee_usd = quote_notional * fee_bps / 10_000.0
    base_asset, quote_asset = _asset_pair(symbol)
    signed_qty = fill_qty if side == "BUY" else -fill_qty
    quote_delta = -quote_notional - fee_usd if side == "BUY" else quote_notional - fee_usd
    return {
        "contract_version": CONTRACT_VERSION,
        "event_type": "internal_paper_sandbox_dry_run_execution_simulated_fill_no_exchange_submit",
        "event_id": f"paper-exec-4B436630N-{current_ms}",
        "generated_at_utc": utc_now_iso(),
        "source_30m_decision": source_30m_snapshot.get("decision"),
        "source_30m_report_path": source_report_path,
        "source_order_envelope_id": order_envelope.get("envelope_id"),
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "side": side,
        "order_type": order_type,
        "quote_notional_usd": quote_notional,
        "simulated_fill_price_usd": fill_price,
        "simulated_fill_qty": fill_qty,
        "signed_position_qty_delta": signed_qty,
        "quote_balance_delta_usd": quote_delta,
        "base_balance_delta": signed_qty,
        "simulated_fee_bps": fee_bps,
        "simulated_fee_usd": fee_usd,
        "paper_sandbox_candidate": True,
        "paper_sandbox_dry_run_execution_authorized": True,
        "paper_sandbox_dry_run_execution_performed": True,
        "network_submit_attempted": False,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
        "runtime_envelope": str(order_envelope.get("runtime_envelope") or _setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "sandbox_only"),
        "execution_mode": str(order_envelope.get("execution_mode") or _setting(settings, "execution_mode", "dry_run") or "dry_run"),
        "market_type": str(order_envelope.get("market_type") or _setting(settings, "market_type", "spot_demo") or "spot_demo"),
    }


def evaluate_internal_paper_execution_simulation(
    settings: Any,
    source_30m_snapshot: Mapping[str, Any],
    order_envelope: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    ledger_path: str | os.PathLike[str] | None = None,
    append_ledger: bool = False,
    now_ms: int | None = None,
) -> PaperExecutionSimulationStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_execution_ledger_append_required", True))
    resolved_ledger = Path(ledger_path) if ledger_path is not None else Path(str(_setting(settings, "paper_sandbox_dry_run_execution_ledger_path", "") or "") or default_ledger_path(DEFAULT_REPORTS_DIR))
    event = build_execution_event(settings, source_30m_snapshot, order_envelope, source_report_path=source_report_path, now_ms=now_ms)
    symbol = str(event.get("symbol") or "UNKNOWN")
    side = str(event.get("side") or "UNKNOWN")
    order_type = str(event.get("order_type") or "UNKNOWN")
    quote_notional = _float(event.get("quote_notional_usd"), 0.0)
    fill_price = _float(event.get("simulated_fill_price_usd"), 0.0)
    fill_qty = _float(event.get("simulated_fill_qty"), 0.0)
    fee_bps = _float(event.get("simulated_fee_bps"), 0.0)
    fee_usd = _float(event.get("simulated_fee_usd"), 0.0)
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_EXECUTION_LEDGER_APPEND_MUST_REMAIN_REQUIRED")
    if not order_envelope:
        reasons.append("ORDER_ENVELOPE_REQUIRED_FOR_INTERNAL_EXECUTION")
    if quote_notional <= 0 or fill_price <= 0 or fill_qty <= 0:
        reasons.append("SIMULATED_FILL_VALUES_INVALID")
    if bool(event.get("network_submit_attempted")) or bool(event.get("submitted_to_exchange")) or bool(event.get("exchange_submit_performed")):
        reasons.append("INTERNAL_EXECUTION_UNEXPECTEDLY_ATTEMPTED_NETWORK_SUBMIT")
    if append_ledger and not reasons:
        append_jsonl_atomic(resolved_ledger, event)
    ledger_appended = bool(append_ledger and not reasons and resolved_ledger.exists())
    ok = required and not reasons and (ledger_appended if append_ledger else True)
    return PaperExecutionSimulationStatus(
        ok=ok,
        required=required,
        execution_simulated=not reasons,
        ledger_appended=ledger_appended,
        ledger_path=str(resolved_ledger),
        event=event,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quote_notional_usd=quote_notional,
        simulated_fill_price_usd=fill_price,
        simulated_fill_qty=fill_qty,
        simulated_fee_bps=fee_bps,
        simulated_fee_usd=fee_usd,
        net_quote_delta_usd=_float(event.get("quote_balance_delta_usd"), 0.0),
        net_base_delta=_float(event.get("base_balance_delta"), 0.0),
        network_submit_allowed=False,
        reason_codes=reasons or ["INTERNAL_PAPER_EXECUTION_SIMULATION_LEDGER_APPENDED_NO_SUBMIT" if ledger_appended else "INTERNAL_PAPER_EXECUTION_SIMULATION_READY_NO_SUBMIT"],
    )


def evaluate_no_exchange_submit(settings: Any, source_30m_snapshot: Mapping[str, Any], simulation: PaperExecutionSimulationStatus | None = None) -> NoExchangeSubmitStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_execution_no_exchange_submit_required", True))
    approved = bool(source_30m_snapshot.get("approved_for_exchange_submit", False))
    exchange_performed = bool(source_30m_snapshot.get("exchange_submit_performed", False)) or bool(_mapping(simulation.event if simulation else {}).get("exchange_submit_performed", False))
    network_attempted = bool(source_30m_snapshot.get("network_submit_attempted", False)) or bool(_mapping(simulation.event if simulation else {}).get("network_submit_attempted", False))
    submitted = bool(_mapping(simulation.event if simulation else {}).get("submitted_to_exchange", False))
    exchange_order_id_present = bool(source_30m_snapshot.get("exchange_order_id_present", False)) or bool(_mapping(simulation.event if simulation else {}).get("exchange_order_id"))
    exchange_client_order_id_present = bool(source_30m_snapshot.get("exchange_client_order_id_present", False)) or bool(_mapping(simulation.event if simulation else {}).get("exchange_client_order_id"))
    reasons: list[str] = []
    if not required:
        reasons.append("NO_EXCHANGE_SUBMIT_GATE_MUST_REMAIN_REQUIRED")
    if approved or exchange_performed or network_attempted or submitted:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED_OR_PERFORMED")
    if exchange_order_id_present:
        reasons.append("EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if exchange_client_order_id_present:
        reasons.append("EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return NoExchangeSubmitStatus(
        ok=required and not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        submitted_to_exchange=submitted,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        exchange_order_id_present=exchange_order_id_present,
        exchange_client_order_id_present=exchange_client_order_id_present,
        reason_codes=reasons or ["NO_EXCHANGE_SUBMIT_VERIFIED_INTERNAL_PAPER_EXECUTION"],
    )


def evaluate_no_live_real(settings: Any, source_30m_snapshot: Mapping[str, Any]) -> NoLiveRealStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_execution_no_live_real_required", True))
    approved_live_real = bool(source_30m_snapshot.get("approved_for_live_real", False))
    live_armed = bool(_setting(settings, "live_trading_armed", False))
    live_confirm = bool(_setting(settings, "live_real_double_confirm", False))
    exchange_performed = bool(source_30m_snapshot.get("exchange_submit_performed", False))
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
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_INTERNAL_PAPER_EXECUTION"],
    )


def build_paper_sandbox_dry_run_execution_snapshot(
    settings: Any,
    source_30m_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    order_envelope: Mapping[str, Any] | None = None,
    operator_id: str | None = None,
    authorization_token: str | None = None,
    issue_execution_authorization: bool = False,
    append_ledger: bool = False,
    ledger_path: str | os.PathLike[str] | None = None,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    envelope = dict(order_envelope or {})
    source = evaluate_source_30m_order_envelope(source_30m_snapshot, source_report_path=source_report_path)
    auth = evaluate_paper_dry_run_execution_authorization(
        settings,
        operator_id=operator_id,
        authorization_token=authorization_token,
        issue_execution_authorization=issue_execution_authorization,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )
    simulation = evaluate_internal_paper_execution_simulation(
        settings,
        source_30m_snapshot,
        envelope,
        source_report_path=source_report_path,
        ledger_path=ledger_path,
        append_ledger=bool(append_ledger and source.ok and auth.ok),
        now_ms=now_ms,
    )
    no_submit = evaluate_no_exchange_submit(settings, source_30m_snapshot, simulation)
    no_live = evaluate_no_live_real(settings, source_30m_snapshot)
    reasons = [*source.reason_codes, *auth.reason_codes, *simulation.reason_codes, *no_submit.reason_codes, *no_live.reason_codes]
    reasons.extend(["INTERNAL_PAPER_EXECUTION_NO_EXCHANGE_SUBMIT", "NO_LIVE_REAL_VERIFIED", "PAPER_EXECUTION_GATE_INTERNAL_ONLY"])
    ready = source.ok and auth.ok and simulation.ok and simulation.ledger_appended and no_submit.ok and no_live.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30M_REQUIRED_DECISION
    elif not auth.ok:
        decision = AUTHORIZATION_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = PaperSandboxDryRunExecutionDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_dry_run_execution_gate=ready,
        approved_for_30m_order_envelope_consumption=source.ok,
        approved_for_internal_paper_execution_simulation=simulation.execution_simulated and auth.ok and source.ok,
        approved_for_paper_execution_ledger_append=simulation.ledger_appended,
        approved_for_paper_sandbox_dry_run_execution=ready,
        approved_for_exchange_submit=False,
        approved_for_paper_candidate=True,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30m_order_envelope_verified=source.ok,
        paper_dry_run_execution_authorization_verified=auth.ok,
        internal_paper_execution_simulated=simulation.execution_simulated and auth.ok and source.ok,
        paper_execution_ledger_appended=simulation.ledger_appended,
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
        source_30m=source.to_dict(),
        paper_dry_run_execution_authorization=auth.to_dict(),
        internal_paper_execution_simulation=simulation.to_dict(),
        no_exchange_submit=no_submit.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30m_snapshot=dict(source_30m_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30m_order_envelope_gate": True,
        "paper_sandbox_dry_run_execution_authorization_gate": True,
        "internal_paper_execution_simulation_gate": True,
        "paper_execution_ledger_append_gate": True,
        "no_exchange_submit_gate": True,
        "no_live_real_gate": True,
        "paper_sandbox_dry_run_execution_performed_internal_only": ready,
        "paper_execution_ledger_path": simulation.ledger_path,
    })
    return payload


def build_from_latest_30m_ready_report(
    settings: Any | None = None,
    *,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    operator_id: str | None = None,
    authorization_token: str | None = None,
    issue_execution_authorization: bool = False,
    append_ledger: bool = False,
    ledger_path: str | os.PathLike[str] | None = None,
    ttl_sec: int | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    latest = latest_30m_ready_report(reports_dir)
    source_snapshot: Mapping[str, Any]
    if latest is None:
        source_snapshot = {}
        source_path: str | None = None
    else:
        loaded = load_json(latest)
        source_snapshot = _mapping(loaded)
        source_path = str(latest)
    envelope = _order_envelope_from_source_or_file(resolved_settings, source_snapshot, reports_dir)
    resolved_ledger_path = ledger_path
    if resolved_ledger_path is None:
        configured = str(_setting(resolved_settings, "paper_sandbox_dry_run_execution_ledger_path", "") or "").strip()
        resolved_ledger_path = Path(configured) if configured else default_ledger_path(reports_dir)
    return build_paper_sandbox_dry_run_execution_snapshot(
        resolved_settings,
        source_snapshot,
        source_report_path=source_path,
        order_envelope=envelope,
        operator_id=operator_id,
        authorization_token=authorization_token,
        issue_execution_authorization=issue_execution_authorization,
        append_ledger=append_ledger,
        ledger_path=resolved_ledger_path,
        ttl_sec=ttl_sec,
        now_ms=now_ms,
    )


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    reports = Path(reports_dir)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "authorization_required" if payload.get("decision") == AUTHORIZATION_REQUIRED_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = reports / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, payload)
    lines = [
        f"# {CONTRACT_VERSION} Paper Sandbox Dry-run Execution Gate",
        "",
        "This report consumes the 30M order envelope, performs internal paper execution simulation, appends a paper execution ledger event when authorized, and keeps exchange submit and live-real blocked.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `read_only`: `{payload.get('read_only')}`",
        f"- `approved_for_paper_sandbox_dry_run_execution_gate`: `{payload.get('approved_for_paper_sandbox_dry_run_execution_gate')}`",
        f"- `approved_for_30m_order_envelope_consumption`: `{payload.get('approved_for_30m_order_envelope_consumption')}`",
        f"- `approved_for_internal_paper_execution_simulation`: `{payload.get('approved_for_internal_paper_execution_simulation')}`",
        f"- `approved_for_paper_execution_ledger_append`: `{payload.get('approved_for_paper_execution_ledger_append')}`",
        f"- `approved_for_paper_sandbox_dry_run_execution`: `{payload.get('approved_for_paper_sandbox_dry_run_execution')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_paper_candidate`: `{payload.get('approved_for_paper_candidate')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        f"- `paper_order_enablement_still_blocked`: `{payload.get('paper_order_enablement_still_blocked')}`",
        f"- `trading_action_performed`: `{payload.get('trading_action_performed')}`",
        f"- `exchange_submit_performed`: `{payload.get('exchange_submit_performed')}`",
        "",
        "## Gate checks",
        f"- `source_30m_order_envelope_verified`: `{payload.get('source_30m_order_envelope_verified')}`",
        f"- `paper_dry_run_execution_authorization_verified`: `{payload.get('paper_dry_run_execution_authorization_verified')}`",
        f"- `internal_paper_execution_simulated`: `{payload.get('internal_paper_execution_simulated')}`",
        f"- `paper_execution_ledger_appended`: `{payload.get('paper_execution_ledger_appended')}`",
        f"- `no_exchange_submit_verified`: `{payload.get('no_exchange_submit_verified')}`",
        f"- `no_live_real_verified`: `{payload.get('no_live_real_verified')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
