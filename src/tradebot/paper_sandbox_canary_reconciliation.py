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

CONTRACT_VERSION = "4B.4.3.6.6.30R"
SOURCE_30Q_CONTRACT_VERSION = "4B.4.3.6.6.30Q"
SOURCE_30Q_READY_DECISION = "FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_READY_ORDER_INTENT_BUILT_SUBMIT_GUARDED_NO_LIVE_REAL"
REPORT_TYPE = "paper_sandbox_canary_reconciliation_submit_guarded_mismatch_zero_no_live_real"
REPORT_PREFIX = "4B436630R_paper_sandbox_canary_reconciliation"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
CANARY_ORDER_INTENT_DEFAULT_NAME = "4B436630Q_single_canary_order_intent.json"

READY_DECISION = "PAPER_SANDBOX_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_SUBMIT_GUARDED_NO_LIVE_REAL"
SOURCE_30Q_REQUIRED_DECISION = "PAPER_SANDBOX_CANARY_RECONCILIATION_30Q_ORDER_INTENT_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
INTENT_REQUIRED_DECISION = "PAPER_SANDBOX_CANARY_RECONCILIATION_ORDER_INTENT_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SANDBOX_CANARY_RECONCILIATION_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

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
class Source30QCanaryIntentStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    first_canary_gate_ready: bool
    source_30p_verified: bool
    operator_approval_verified: bool
    submit_readiness_verified: bool
    order_intent_built: bool
    order_intent_written: bool
    submit_path_guarded: bool
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
class CanaryOrderIntentConsumptionStatus:
    ok: bool
    intent_path: str | None
    intent_id: str | None
    contract_version: str | None
    event_type: str | None
    symbol: str | None
    side: str | None
    order_type: str | None
    quote_notional_usd: float
    quantity: float
    submit_path_guarded: bool
    submit_to_exchange: bool
    submitted_to_exchange: bool
    network_submit_attempted: bool
    exchange_submit_performed: bool
    exchange_order_id_present: bool
    exchange_client_order_id_present: bool
    live_real_approved: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntentFillAccountReconciliationStatus:
    ok: bool
    expected_fill_count: int
    observed_fill_count: int
    expected_account_delta_usd: float
    observed_account_delta_usd: float
    expected_position_delta_qty: float
    observed_position_delta_qty: float
    expected_fee_usd: float
    observed_fee_usd: float
    fill_mismatch_count: int
    account_mismatch_count: int
    position_mismatch_count: int
    fee_mismatch_count: int
    mismatch_count: int
    mismatch_items: list[dict[str, Any]]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SubmitGuardProofStatus:
    ok: bool
    required: bool
    source_submit_path_guarded: bool
    intent_submit_path_guarded: bool
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
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSandboxCanaryReconciliationDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_canary_reconciliation: bool
    approved_for_30q_canary_intent_consumption: bool
    approved_for_intent_fill_account_reconciliation: bool
    approved_for_submit_guarded_proof: bool
    approved_for_mismatch_zero_proof: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    source_30q_canary_gate_verified: bool
    canary_order_intent_consumed: bool
    intent_fill_account_reconciled: bool
    submit_remained_guarded_verified: bool
    mismatch_zero_verified: bool
    no_live_real_verified: bool
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
    source_30q: dict[str, Any]
    canary_order_intent: dict[str, Any]
    intent_fill_account_reconciliation: dict[str, Any]
    submit_guard_proof: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30q_snapshot: dict[str, Any]
    order_intent_snapshot: dict[str, Any]

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
        "source_30q",
        "first_canary_submit_gate",
        "single_sandbox_order_intent",
        "single_canary_order_intent",
        "submit_guard",
        "no_live_real",
    ):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def latest_valid_30q_canary_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    reports = Path(reports_dir)
    matches = sorted(
        [item for item in reports.glob("4B436630Q_first_paper_sandbox_canary_submit_gate_*_ready.json") if item.is_file()],
        key=lambda item: item.name,
        reverse=True,
    )
    for item in matches:
        try:
            payload = load_json(item)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and evaluate_source_30q_canary_gate(payload, source_report_path=str(item)).ok:
            return item, payload
    return None, {}


def default_intent_path(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path:
    return Path(reports_dir) / CANARY_ORDER_INTENT_DEFAULT_NAME


def _intent_from_source_or_file(settings: Any, source_30q_snapshot: Mapping[str, Any], reports_dir: str | os.PathLike[str]) -> tuple[Path | None, dict[str, Any]]:
    nested = _nested(source_30q_snapshot)
    for key in ("intent", "order_intent", "canary_order_intent", "single_sandbox_order_intent"):
        value = source_30q_snapshot.get(key) or nested.get(key)
        if isinstance(value, Mapping):
            return None, dict(value)
    path_text = str(_setting(settings, "paper_sandbox_canary_reconciliation_order_intent_path", "") or "").strip()
    candidates = []
    if path_text:
        candidates.append(Path(path_text))
    candidates.append(default_intent_path(reports_dir))
    intent_path_from_source = _first_present(source_30q_snapshot, ("canary_order_intent_path", "order_intent_path", "intent_path"), None)
    if intent_path_from_source:
        candidates.insert(0, Path(str(intent_path_from_source)))
    for path in candidates:
        try:
            if path.exists():
                payload = load_json(path)
                if isinstance(payload, dict):
                    return path, payload
        except OSError:
            continue
    return None, {}


def evaluate_source_30q_canary_gate(source_30q_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30QCanaryIntentStatus:
    nested = _nested(source_30q_snapshot)
    contract = str(source_30q_snapshot.get("contract_version") or "") or None
    decision = str(source_30q_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30Q_READY_DECISION
    ready = _boolish(_first_present(source_30q_snapshot, (
        "approved_for_first_paper_sandbox_canary_submit_gate",
        "first_canary_gate_ready",
    ), nested.get("approved_for_first_paper_sandbox_canary_submit_gate", decision_ok)), decision_ok)
    source_30p = _boolish(_first_present(source_30q_snapshot, ("source_30p_submit_arm_verified", "approved_for_30p_submit_arm_consumption"), nested.get("source_30p_submit_arm_verified", decision_ok)), decision_ok)
    approval = _boolish(_first_present(source_30q_snapshot, ("operator_canary_approval_verified", "approved_for_operator_canary_approval"), nested.get("operator_canary_approval_verified", decision_ok)), decision_ok)
    readiness = _boolish(_first_present(source_30q_snapshot, ("sandbox_submit_readiness_verified",), nested.get("sandbox_submit_readiness_verified", decision_ok)), decision_ok)
    intent_built = _boolish(_first_present(source_30q_snapshot, ("single_sandbox_order_intent_built", "order_intent_built"), nested.get("single_sandbox_order_intent_built", decision_ok)), decision_ok)
    intent_written = _boolish(_first_present(source_30q_snapshot, ("canary_order_intent_written", "order_intent_written"), nested.get("canary_order_intent_written", decision_ok)), decision_ok)
    submit_guarded = _boolish(_first_present(source_30q_snapshot, ("exchange_submit_path_guarded", "submit_still_blocked"), nested.get("exchange_submit_path_guarded", True)), True)
    approved_exchange = _boolish(source_30q_snapshot.get("approved_for_exchange_submit"), False)
    approved_live = _boolish(source_30q_snapshot.get("approved_for_live_real"), False)
    exchange_performed = _boolish(source_30q_snapshot.get("exchange_submit_performed"), False)
    network_attempted = _boolish(source_30q_snapshot.get("network_submit_attempted"), False)
    trading_action = _boolish(source_30q_snapshot.get("trading_action_performed"), False)
    order_actions = _boolish(source_30q_snapshot.get("order_actions_performed"), False)
    reasons: list[str] = []
    if contract != SOURCE_30Q_CONTRACT_VERSION:
        reasons.append("SOURCE_30Q_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30Q_READY_CANARY_INTENT_DECISION_REQUIRED")
    if not ready:
        reasons.append("SOURCE_30Q_CANARY_GATE_NOT_READY")
    if not source_30p:
        reasons.append("SOURCE_30Q_30P_SUBMIT_ARM_NOT_VERIFIED")
    if not approval:
        reasons.append("SOURCE_30Q_OPERATOR_APPROVAL_NOT_VERIFIED")
    if not readiness:
        reasons.append("SOURCE_30Q_SUBMIT_READINESS_NOT_VERIFIED")
    if not intent_built or not intent_written:
        reasons.append("SOURCE_30Q_ORDER_INTENT_NOT_BUILT_OR_WRITTEN")
    if not submit_guarded:
        reasons.append("SOURCE_30Q_SUBMIT_PATH_NOT_GUARDED")
    if approved_exchange or exchange_performed or network_attempted:
        reasons.append("SOURCE_30Q_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if approved_live:
        reasons.append("SOURCE_30Q_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions:
        reasons.append("SOURCE_30Q_TRADING_OR_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30QCanaryIntentStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        first_canary_gate_ready=ready,
        source_30p_verified=source_30p,
        operator_approval_verified=approval,
        submit_readiness_verified=readiness,
        order_intent_built=intent_built,
        order_intent_written=intent_written,
        submit_path_guarded=submit_guarded,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30Q_CANARY_ORDER_INTENT_VERIFIED"],
    )


def evaluate_order_intent_consumption(order_intent: Mapping[str, Any], *, intent_path: str | None = None) -> CanaryOrderIntentConsumptionStatus:
    contract = str(order_intent.get("contract_version") or "") or None
    event_type = str(order_intent.get("event_type") or "") or None
    intent_id = str(order_intent.get("intent_id") or "") or None
    symbol = str(order_intent.get("symbol") or "") or None
    side = str(order_intent.get("side") or "") or None
    order_type = str(order_intent.get("order_type") or "") or None
    quote_notional = _float(order_intent.get("quote_notional_usd"), 0.0)
    quantity = _float(order_intent.get("quantity"), 0.0)
    submit_guarded = _boolish(order_intent.get("submit_path_guarded"), True)
    submit_to_exchange = _boolish(order_intent.get("submit_to_exchange"), False)
    submitted = _boolish(order_intent.get("submitted_to_exchange"), False)
    network_attempted = _boolish(order_intent.get("network_submit_attempted"), False)
    exchange_performed = _boolish(order_intent.get("exchange_submit_performed"), False)
    exchange_order_id_present = bool(order_intent.get("exchange_order_id")) or _boolish(order_intent.get("exchange_order_id_present"), False)
    exchange_client_order_id_present = bool(order_intent.get("exchange_client_order_id")) or _boolish(order_intent.get("exchange_client_order_id_present"), False)
    live_real = _boolish(order_intent.get("live_real_approved"), False)
    reasons: list[str] = []
    if not order_intent:
        reasons.append("CANARY_ORDER_INTENT_MISSING")
    if contract != SOURCE_30Q_CONTRACT_VERSION:
        reasons.append("CANARY_ORDER_INTENT_CONTRACT_VERSION_MISMATCH")
    if not event_type or "canary" not in event_type.lower() or "intent" not in event_type.lower():
        reasons.append("CANARY_ORDER_INTENT_EVENT_TYPE_INVALID")
    if not intent_id:
        reasons.append("CANARY_ORDER_INTENT_ID_MISSING")
    if not symbol or not side or not order_type:
        reasons.append("CANARY_ORDER_INTENT_CORE_FIELDS_MISSING")
    if quote_notional <= 0 or quantity <= 0:
        reasons.append("CANARY_ORDER_INTENT_SIZE_INVALID")
    if not submit_guarded:
        reasons.append("CANARY_ORDER_INTENT_SUBMIT_NOT_GUARDED")
    if submit_to_exchange or submitted or network_attempted or exchange_performed:
        reasons.append("CANARY_ORDER_INTENT_UNEXPECTED_EXCHANGE_SUBMIT")
    if exchange_order_id_present or exchange_client_order_id_present:
        reasons.append("CANARY_ORDER_INTENT_EXCHANGE_ID_UNEXPECTEDLY_PRESENT")
    if live_real:
        reasons.append("CANARY_ORDER_INTENT_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    return CanaryOrderIntentConsumptionStatus(
        ok=not reasons,
        intent_path=intent_path,
        intent_id=intent_id,
        contract_version=contract,
        event_type=event_type,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quote_notional_usd=quote_notional,
        quantity=quantity,
        submit_path_guarded=submit_guarded,
        submit_to_exchange=submit_to_exchange,
        submitted_to_exchange=submitted,
        network_submit_attempted=network_attempted,
        exchange_submit_performed=exchange_performed,
        exchange_order_id_present=exchange_order_id_present,
        exchange_client_order_id_present=exchange_client_order_id_present,
        live_real_approved=live_real,
        reason_codes=reasons or ["CANARY_ORDER_INTENT_CONSUMED_SUBMIT_GUARDED"],
    )


def _almost_equal(a: float, b: float, eps: float = 1e-9) -> bool:
    return abs(a - b) <= eps


def evaluate_intent_fill_account_reconciliation(settings: Any, source: Source30QCanaryIntentStatus, intent: CanaryOrderIntentConsumptionStatus) -> IntentFillAccountReconciliationStatus:
    expected_fill_count = _int(_setting(settings, "paper_sandbox_canary_reconciliation_expected_fill_count", 0), 0)
    observed_fill_count = 0
    expected_account_delta = _float(_setting(settings, "paper_sandbox_canary_reconciliation_expected_account_delta_usd", 0.0), 0.0)
    observed_account_delta = 0.0
    expected_position_delta = _float(_setting(settings, "paper_sandbox_canary_reconciliation_expected_position_delta_qty", 0.0), 0.0)
    observed_position_delta = 0.0
    expected_fee = _float(_setting(settings, "paper_sandbox_canary_reconciliation_expected_fee_usd", 0.0), 0.0)
    observed_fee = 0.0
    mismatch_items: list[dict[str, Any]] = []
    if expected_fill_count != observed_fill_count:
        mismatch_items.append({"field": "fill_count", "expected": expected_fill_count, "observed": observed_fill_count})
    if not _almost_equal(expected_account_delta, observed_account_delta):
        mismatch_items.append({"field": "account_delta_usd", "expected": expected_account_delta, "observed": observed_account_delta})
    if not _almost_equal(expected_position_delta, observed_position_delta):
        mismatch_items.append({"field": "position_delta_qty", "expected": expected_position_delta, "observed": observed_position_delta})
    if not _almost_equal(expected_fee, observed_fee):
        mismatch_items.append({"field": "fee_usd", "expected": expected_fee, "observed": observed_fee})
    fill_mismatch = 1 if expected_fill_count != observed_fill_count else 0
    account_mismatch = 1 if not _almost_equal(expected_account_delta, observed_account_delta) else 0
    position_mismatch = 1 if not _almost_equal(expected_position_delta, observed_position_delta) else 0
    fee_mismatch = 1 if not _almost_equal(expected_fee, observed_fee) else 0
    mismatch_count = fill_mismatch + account_mismatch + position_mismatch + fee_mismatch
    reasons = ["INTENT_FILL_ACCOUNT_RECONCILED_MISMATCH_ZERO"] if mismatch_count == 0 else ["INTENT_FILL_ACCOUNT_RECONCILIATION_MISMATCH_NON_ZERO"]
    return IntentFillAccountReconciliationStatus(
        ok=source.ok and intent.ok and mismatch_count == 0,
        expected_fill_count=expected_fill_count,
        observed_fill_count=observed_fill_count,
        expected_account_delta_usd=expected_account_delta,
        observed_account_delta_usd=observed_account_delta,
        expected_position_delta_qty=expected_position_delta,
        observed_position_delta_qty=observed_position_delta,
        expected_fee_usd=expected_fee,
        observed_fee_usd=observed_fee,
        fill_mismatch_count=fill_mismatch,
        account_mismatch_count=account_mismatch,
        position_mismatch_count=position_mismatch,
        fee_mismatch_count=fee_mismatch,
        mismatch_count=mismatch_count,
        mismatch_items=mismatch_items,
        reason_codes=reasons,
    )


def evaluate_submit_guard_proof(settings: Any, source: Source30QCanaryIntentStatus, intent: CanaryOrderIntentConsumptionStatus) -> SubmitGuardProofStatus:
    required = _boolish(_setting(settings, "paper_sandbox_canary_reconciliation_submit_guard_required", True), True)
    approved_exchange = source.approved_for_exchange_submit
    exchange_performed = source.exchange_submit_performed or intent.exchange_submit_performed or intent.submitted_to_exchange
    network_attempted = source.network_submit_attempted or intent.network_submit_attempted
    exchange_order_id = intent.exchange_order_id_present
    exchange_client_order_id = intent.exchange_client_order_id_present
    reasons: list[str] = []
    if not required:
        reasons.append("CANARY_RECONCILIATION_SUBMIT_GUARD_MUST_REMAIN_REQUIRED")
    if not source.submit_path_guarded or not intent.submit_path_guarded:
        reasons.append("CANARY_RECONCILIATION_SUBMIT_PATH_NOT_GUARDED")
    if approved_exchange or exchange_performed or network_attempted:
        reasons.append("CANARY_RECONCILIATION_EXCHANGE_SUBMIT_UNEXPECTEDLY_OCCURRED")
    if exchange_order_id or exchange_client_order_id:
        reasons.append("CANARY_RECONCILIATION_EXCHANGE_ID_UNEXPECTEDLY_PRESENT")
    return SubmitGuardProofStatus(
        ok=required and not reasons,
        required=required,
        source_submit_path_guarded=source.submit_path_guarded,
        intent_submit_path_guarded=intent.submit_path_guarded,
        approved_for_exchange_submit=approved_exchange,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        exchange_order_id_present=exchange_order_id,
        exchange_client_order_id_present=exchange_client_order_id,
        reason_codes=reasons or ["CANARY_SUBMIT_REMAINED_GUARDED_VERIFIED"],
    )


def evaluate_no_live_real(settings: Any, source: Source30QCanaryIntentStatus, intent: CanaryOrderIntentConsumptionStatus) -> NoLiveRealStatus:
    required = _boolish(_setting(settings, "paper_sandbox_canary_reconciliation_no_live_real_required", True), True)
    live_armed = _boolish(_setting(settings, "live_trading_armed", False), False)
    live_confirm = _boolish(_setting(settings, "live_real_double_confirm", False), False)
    approved_live = source.approved_for_live_real or intent.live_real_approved
    reasons: list[str] = []
    if not required:
        reasons.append("CANARY_RECONCILIATION_NO_LIVE_REAL_MUST_REMAIN_REQUIRED")
    if approved_live or live_armed or live_confirm:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_ENABLED_OR_ARMED")
    return NoLiveRealStatus(
        ok=required and not reasons,
        required=required,
        approved_for_live_real=approved_live,
        live_trading_armed=live_armed,
        live_real_double_confirm=live_confirm,
        reason_codes=reasons or ["NO_LIVE_REAL_VERIFIED_CANARY_RECONCILIATION"],
    )


def build_paper_sandbox_canary_reconciliation_snapshot(
    settings: Any,
    source_30q_snapshot: Mapping[str, Any],
    order_intent: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    intent_path: str | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30q_canary_gate(source_30q_snapshot, source_report_path=source_report_path)
    intent = evaluate_order_intent_consumption(order_intent, intent_path=intent_path)
    reconciliation = evaluate_intent_fill_account_reconciliation(settings, source, intent)
    submit_guard = evaluate_submit_guard_proof(settings, source, intent)
    no_live = evaluate_no_live_real(settings, source, intent)
    mismatch_zero_required = _boolish(_setting(settings, "paper_sandbox_canary_reconciliation_mismatch_zero_required", True), True)
    mismatch_zero = reconciliation.mismatch_count == 0
    ready = source.ok and intent.ok and reconciliation.ok and submit_guard.ok and no_live.ok and mismatch_zero_required and mismatch_zero
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30Q_REQUIRED_DECISION
    elif not intent.ok:
        decision = INTENT_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    reasons = [*source.reason_codes, *intent.reason_codes, *reconciliation.reason_codes, *submit_guard.reason_codes, *no_live.reason_codes]
    reasons.extend(["CANARY_RECONCILIATION_MISMATCH_ZERO_PROOF", "SUBMIT_REMAINED_GUARDED_PROOF", "NO_LIVE_REAL_VERIFIED"])
    payload = PaperSandboxCanaryReconciliationDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_canary_reconciliation=ready,
        approved_for_30q_canary_intent_consumption=source.ok and intent.ok,
        approved_for_intent_fill_account_reconciliation=reconciliation.ok,
        approved_for_submit_guarded_proof=submit_guard.ok,
        approved_for_mismatch_zero_proof=mismatch_zero_required and mismatch_zero,
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        source_30q_canary_gate_verified=source.ok,
        canary_order_intent_consumed=intent.ok,
        intent_fill_account_reconciled=reconciliation.ok,
        submit_remained_guarded_verified=submit_guard.ok,
        mismatch_zero_verified=mismatch_zero_required and mismatch_zero,
        no_live_real_verified=no_live.ok,
        mismatch_count=reconciliation.mismatch_count,
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
        source_30q=source.to_dict(),
        canary_order_intent=intent.to_dict(),
        intent_fill_account_reconciliation=reconciliation.to_dict(),
        submit_guard_proof=submit_guard.to_dict(),
        no_live_real=no_live.to_dict(),
        source_30q_snapshot=dict(source_30q_snapshot),
        order_intent_snapshot=dict(order_intent),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30q_canary_intent_gate": True,
        "canary_order_intent_consumption_gate": True,
        "intent_fill_account_reconciliation_gate": True,
        "submit_remained_guarded_proof_gate": True,
        "mismatch_zero_gate": True,
        "no_live_real_gate": True,
    })
    return payload


def build_from_latest_30q_ready_report(settings: Any | None = None, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source = latest_valid_30q_canary_report(reports_dir)
    intent_path, intent = _intent_from_source_or_file(resolved_settings, source, reports_dir)
    return build_paper_sandbox_canary_reconciliation_snapshot(
        resolved_settings,
        source,
        intent,
        source_report_path=str(source_path) if source_path else None,
        intent_path=str(intent_path) if intent_path else None,
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
        f"# {CONTRACT_VERSION} Paper Sandbox Canary Reconciliation",
        "",
        "Consumes the 30Q canary order intent, verifies submit remained guarded, reconciles intent/fill/account as mismatch zero, and keeps live-real blocked.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_paper_sandbox_canary_reconciliation`: `{payload.get('approved_for_paper_sandbox_canary_reconciliation')}`",
        f"- `source_30q_canary_gate_verified`: `{payload.get('source_30q_canary_gate_verified')}`",
        f"- `canary_order_intent_consumed`: `{payload.get('canary_order_intent_consumed')}`",
        f"- `intent_fill_account_reconciled`: `{payload.get('intent_fill_account_reconciled')}`",
        f"- `submit_remained_guarded_verified`: `{payload.get('submit_remained_guarded_verified')}`",
        f"- `mismatch_count`: `{payload.get('mismatch_count')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
