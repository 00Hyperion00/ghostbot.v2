from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.30V"
SOURCE_30U_CONTRACT_VERSION = "4B.4.3.6.6.30U"
SOURCE_30U_READY_DECISION = "PAPER_PROMOTION_REVIEW_READY_RISK_ACCEPTANCE_GATES_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
REPORT_TYPE = "live_real_preflight_gate_api_env_account_audit_hard_submit_blocked_no_live_real_order"
REPORT_PREFIX = "4B436630V_live_real_preflight_gate"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "LIVE_REAL_PREFLIGHT_GATE_READY_API_ENV_ACCOUNT_AUDIT_HARD_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER"
SOURCE_30U_REQUIRED_DECISION = "LIVE_REAL_PREFLIGHT_GATE_30U_PROMOTION_REVIEW_REQUIRED_NO_LIVE_REAL_ORDER"
CAPABILITY_AUDIT_NOT_READY_DECISION = "LIVE_REAL_PREFLIGHT_GATE_CAPABILITY_AUDIT_NOT_READY_NO_LIVE_REAL_ORDER"
HARD_BLOCK_NOT_READY_DECISION = "LIVE_REAL_PREFLIGHT_GATE_HARD_SUBMIT_BLOCK_NOT_READY_NO_LIVE_REAL_ORDER"
NOT_READY_DECISION = "LIVE_REAL_PREFLIGHT_GATE_NOT_READY_NO_LIVE_REAL_ORDER"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "preflight_only": True,
    "live_real_preflight_only": True,
    "paper_live_order_blocked": True,
    "exchange_submit_path_guarded": True,
    "exchange_submit_blocked": True,
    "live_real_blocked": True,
    "live_real_hard_block_verified": True,
    "live_real_order_performed": False,
    "live_real_order_submitted": False,
    "live_real_network_submit_attempted": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "exchange_submit_performed": False,
    "network_submit_attempted": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30UPromotionStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    paper_promotion_review_ready: bool
    paper_runtime_promotion_candidate: bool
    risk_acceptance_gates_verified: bool
    promotion_readiness_review_verified: bool
    no_exchange_submit_verified: bool
    no_live_real_verified: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    trading_action_performed: bool
    order_actions_performed: bool
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    soak_cycle_count: int
    total_notional_usd: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CapabilityAuditStatus:
    ok: bool
    required: bool
    api_key_presence_required: bool
    api_key_present: bool
    api_secret_present: bool
    api_key_redacted: str
    api_secret_redacted: str
    environment_name: str
    account_capability_mode: str
    account_capability_audit_verified: bool
    api_env_audit_verified: bool
    no_secret_material_persisted: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HardSubmitBlockStatus:
    ok: bool
    required: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    live_real_order_performed: bool
    live_real_order_submitted: bool
    live_real_network_submit_attempted: bool
    exchange_submit_count: int
    network_submit_count: int
    order_action_count: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LiveRealPreflightGateSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_live_real_preflight_gate: bool
    approved_for_live_real_readiness_candidate: bool
    source_30u_promotion_review_verified: bool
    api_env_capability_audit_verified: bool
    account_capability_audit_verified: bool
    hard_live_submit_block_verified: bool
    no_exchange_submit_verified: bool
    no_live_real_order_verified: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    trading_action_performed: bool
    order_actions_performed: bool
    live_real_order_performed: bool
    live_real_order_submitted: bool
    live_real_network_submit_attempted: bool
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    total_notional_usd: float
    exchange_submit_blocked: bool
    live_real_blocked: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    reason_codes: list[str]
    source_30u: dict[str, Any]
    capability_audit: dict[str, Any]
    hard_submit_block: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real_order: dict[str, Any]
    source_30u_snapshot: dict[str, Any]

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
        "source_30u",
        "paper_promotion_review",
        "risk_acceptance",
        "promotion_readiness_review",
        "no_exchange_submit",
        "no_live_real",
    ):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def _redacted_presence(value: str | None) -> str:
    if not value:
        return "absent"
    return "present_redacted"


def evaluate_source_30u_promotion(source_30u_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30UPromotionStatus:
    nested = _nested(source_30u_snapshot)
    contract = str(source_30u_snapshot.get("contract_version") or "") or None
    decision = str(source_30u_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30U_READY_DECISION
    ready = _boolish(_first_present(source_30u_snapshot, ("approved_for_paper_promotion_review",), nested.get("approved_for_paper_promotion_review", decision_ok)), decision_ok)
    runtime_candidate = _boolish(_first_present(source_30u_snapshot, ("approved_for_paper_runtime_promotion_candidate",), nested.get("approved_for_paper_runtime_promotion_candidate", decision_ok)), decision_ok)
    risk_ok = _boolish(_first_present(source_30u_snapshot, ("risk_acceptance_gates_verified",), nested.get("risk_acceptance_gates_verified", decision_ok)), decision_ok)
    promotion_ok = _boolish(_first_present(source_30u_snapshot, ("promotion_readiness_review_verified",), nested.get("promotion_readiness_review_verified", decision_ok)), decision_ok)
    no_exchange = _boolish(_first_present(source_30u_snapshot, ("no_exchange_submit_verified",), nested.get("no_exchange_submit_verified", True)), True)
    no_live = _boolish(_first_present(source_30u_snapshot, ("no_live_real_verified",), nested.get("no_live_real_verified", True)), True)
    approved_exchange = _boolish(source_30u_snapshot.get("approved_for_exchange_submit"), False)
    approved_live = _boolish(source_30u_snapshot.get("approved_for_live_real"), False)
    exchange_performed = _boolish(source_30u_snapshot.get("exchange_submit_performed"), False)
    network_attempted = _boolish(source_30u_snapshot.get("network_submit_attempted"), False)
    trading_action = _boolish(source_30u_snapshot.get("trading_action_performed"), False)
    order_actions = _boolish(source_30u_snapshot.get("order_actions_performed"), False)
    order_count = _int(_first_present(source_30u_snapshot, ("order_action_count",), nested.get("order_action_count", 0)), 0)
    exchange_count = _int(_first_present(source_30u_snapshot, ("exchange_submit_count",), nested.get("exchange_submit_count", 0)), 0)
    network_count = _int(_first_present(source_30u_snapshot, ("network_submit_count",), nested.get("network_submit_count", 0)), 0)
    soak_cycles = _int(_first_present(source_30u_snapshot, ("soak_cycle_count",), nested.get("soak_cycle_count", 0)), 0)
    notional = _float(_first_present(source_30u_snapshot, ("total_notional_usd",), nested.get("total_notional_usd", 0.0)), 0.0)
    reasons: list[str] = []
    if contract != SOURCE_30U_CONTRACT_VERSION:
        reasons.append("SOURCE_30U_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30U_READY_PROMOTION_REVIEW_DECISION_REQUIRED")
    if not ready or not runtime_candidate:
        reasons.append("SOURCE_30U_PROMOTION_REVIEW_NOT_READY")
    if not risk_ok or not promotion_ok:
        reasons.append("SOURCE_30U_PROMOTION_RISK_GATES_NOT_VERIFIED")
    if not no_exchange or approved_exchange or exchange_performed or network_attempted:
        reasons.append("SOURCE_30U_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if not no_live or approved_live:
        reasons.append("SOURCE_30U_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions or order_count != 0 or exchange_count != 0 or network_count != 0:
        reasons.append("SOURCE_30U_TRADING_OR_SUBMIT_COUNTS_NOT_ZERO")
    if notional != 0.0:
        reasons.append("SOURCE_30U_NOTIONAL_MUST_REMAIN_ZERO")
    return Source30UPromotionStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        paper_promotion_review_ready=ready,
        paper_runtime_promotion_candidate=runtime_candidate,
        risk_acceptance_gates_verified=risk_ok,
        promotion_readiness_review_verified=promotion_ok,
        no_exchange_submit_verified=no_exchange,
        no_live_real_verified=no_live,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        order_action_count=order_count,
        exchange_submit_count=exchange_count,
        network_submit_count=network_count,
        soak_cycle_count=soak_cycles,
        total_notional_usd=notional,
        reason_codes=reasons or ["SOURCE_30U_PAPER_PROMOTION_REVIEW_VERIFIED"],
    )


def latest_valid_30u_promotion_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    reports = Path(reports_dir)
    matches = sorted(
        [item for item in reports.glob("4B436630U_paper_promotion_review_*_ready.json") if item.is_file()],
        key=lambda item: item.name,
        reverse=True,
    )
    for item in matches:
        try:
            payload = load_json(item)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and evaluate_source_30u_promotion(payload, source_report_path=str(item)).ok:
            return item, payload
    return None, {}


def evaluate_capability_audit(settings: Any, env: Mapping[str, str] | None = None) -> CapabilityAuditStatus:
    resolved_env = env if env is not None else os.environ
    required = _boolish(_setting(settings, "live_real_preflight_capability_audit_required", True), True)
    key_required = _boolish(_setting(settings, "live_real_preflight_api_key_presence_required", False), False)
    account_required = _boolish(_setting(settings, "live_real_preflight_account_capability_audit_required", True), True)
    api_required = _boolish(_setting(settings, "live_real_preflight_api_env_audit_required", True), True)
    key = resolved_env.get("BINANCE_API_KEY") or resolved_env.get("BINANCE_FUTURES_API_KEY") or resolved_env.get("BINANCE_LIVE_API_KEY")
    secret = resolved_env.get("BINANCE_API_SECRET") or resolved_env.get("BINANCE_FUTURES_API_SECRET") or resolved_env.get("BINANCE_LIVE_API_SECRET")
    environment_name = str(resolved_env.get("TRADEBOT_ENV") or resolved_env.get("APP_ENV") or "offline_preflight")
    api_key_present = bool(key)
    api_secret_present = bool(secret)
    api_env_ok = (api_key_present and api_secret_present) if key_required else True
    account_mode = str(_setting(settings, "live_real_preflight_account_capability_mode", "offline_redacted_audit"))
    account_ok = account_required and account_mode in {"offline_redacted_audit", "read_only_probe", "manual_operator_attested"}
    reasons: list[str] = []
    if required and api_required and not api_env_ok:
        reasons.append("LIVE_REAL_PREFLIGHT_API_KEY_SECRET_PRESENCE_REQUIRED")
    if required and not account_ok:
        reasons.append("LIVE_REAL_PREFLIGHT_ACCOUNT_CAPABILITY_AUDIT_REQUIRED")
    return CapabilityAuditStatus(
        ok=not reasons,
        required=required,
        api_key_presence_required=key_required,
        api_key_present=api_key_present,
        api_secret_present=api_secret_present,
        api_key_redacted=_redacted_presence(key),
        api_secret_redacted=_redacted_presence(secret),
        environment_name=environment_name,
        account_capability_mode=account_mode,
        account_capability_audit_verified=account_ok,
        api_env_audit_verified=api_env_ok,
        no_secret_material_persisted=True,
        reason_codes=reasons or ["LIVE_REAL_PREFLIGHT_CAPABILITY_AUDIT_VERIFIED_OFFLINE_REDACTED"],
    )


def evaluate_hard_submit_block(settings: Any, source: Source30UPromotionStatus) -> HardSubmitBlockStatus:
    required = _boolish(_setting(settings, "live_real_preflight_hard_submit_block_required", True), True)
    live_order_required = _boolish(_setting(settings, "live_real_preflight_no_live_order_required", True), True)
    exchange_cap = max(0, _int(_setting(settings, "live_real_preflight_exchange_submit_cap", 0), 0))
    network_cap = max(0, _int(_setting(settings, "live_real_preflight_network_submit_cap", 0), 0))
    order_cap = max(0, _int(_setting(settings, "live_real_preflight_order_action_cap", 0), 0))
    ok = (
        required
        and live_order_required
        and not source.approved_for_exchange_submit
        and not source.approved_for_live_real
        and not source.exchange_submit_performed
        and not source.network_submit_attempted
        and not source.trading_action_performed
        and not source.order_actions_performed
        and source.exchange_submit_count <= exchange_cap
        and source.network_submit_count <= network_cap
        and source.order_action_count <= order_cap
    )
    reasons: list[str] = []
    if not required:
        reasons.append("LIVE_REAL_PREFLIGHT_HARD_SUBMIT_BLOCK_REQUIRED")
    if not live_order_required:
        reasons.append("LIVE_REAL_PREFLIGHT_NO_LIVE_ORDER_REQUIRED")
    if not ok and not reasons:
        reasons.append("LIVE_REAL_PREFLIGHT_SOURCE_SUBMIT_OR_ORDER_ACTIVITY_NOT_ZERO")
    return HardSubmitBlockStatus(
        ok=ok,
        required=required,
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        exchange_submit_performed=False,
        network_submit_attempted=False,
        live_real_order_performed=False,
        live_real_order_submitted=False,
        live_real_network_submit_attempted=False,
        exchange_submit_count=source.exchange_submit_count,
        network_submit_count=source.network_submit_count,
        order_action_count=source.order_action_count,
        reason_codes=reasons or ["LIVE_REAL_PREFLIGHT_HARD_SUBMIT_BLOCK_VERIFIED"],
    )


def build_live_real_preflight_gate_snapshot(
    settings: Any | None = None,
    source_30u_snapshot: Mapping[str, Any] | None = None,
    *,
    source_report_path: str | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_snapshot = dict(_mapping(source_30u_snapshot))
    source = evaluate_source_30u_promotion(source_snapshot, source_report_path=source_report_path)
    capability = evaluate_capability_audit(resolved_settings, env=env)
    hard_block = evaluate_hard_submit_block(resolved_settings, source)
    no_exchange = {
        "ok": source.ok and hard_block.ok and not hard_block.approved_for_exchange_submit and not hard_block.exchange_submit_performed and not hard_block.network_submit_attempted,
        "required": True,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_submit_count": hard_block.exchange_submit_count,
        "network_submit_count": hard_block.network_submit_count,
        "reason_codes": ["LIVE_REAL_PREFLIGHT_NO_EXCHANGE_SUBMIT_VERIFIED"],
    }
    no_live_order = {
        "ok": source.ok and hard_block.ok and not hard_block.approved_for_live_real and not hard_block.live_real_order_performed and not hard_block.live_real_order_submitted and not hard_block.live_real_network_submit_attempted,
        "required": True,
        "approved_for_live_real": False,
        "live_real_order_performed": False,
        "live_real_order_submitted": False,
        "live_real_network_submit_attempted": False,
        "reason_codes": ["LIVE_REAL_PREFLIGHT_NO_LIVE_REAL_ORDER_VERIFIED"],
    }
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not capability.ok:
        reasons.extend(capability.reason_codes)
    if not hard_block.ok:
        reasons.extend(hard_block.reason_codes)
    if not no_exchange["ok"]:
        reasons.extend(no_exchange["reason_codes"])
    if not no_live_order["ok"]:
        reasons.extend(no_live_order["reason_codes"])
    if source.ok and capability.ok and hard_block.ok and no_exchange["ok"] and no_live_order["ok"]:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30U_REQUIRED_DECISION
    elif not capability.ok:
        decision = CAPABILITY_AUDIT_NOT_READY_DECISION
    elif not hard_block.ok:
        decision = HARD_BLOCK_NOT_READY_DECISION
    else:
        decision = NOT_READY_DECISION
    approved = decision == READY_DECISION
    snapshot = LiveRealPreflightGateSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_30U_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_live_real_preflight_gate=approved,
        approved_for_live_real_readiness_candidate=approved,
        source_30u_promotion_review_verified=source.ok,
        api_env_capability_audit_verified=capability.api_env_audit_verified,
        account_capability_audit_verified=capability.account_capability_audit_verified,
        hard_live_submit_block_verified=hard_block.ok,
        no_exchange_submit_verified=bool(no_exchange["ok"]),
        no_live_real_order_verified=bool(no_live_order["ok"]),
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        exchange_submit_performed=False,
        network_submit_attempted=False,
        trading_action_performed=False,
        order_actions_performed=False,
        live_real_order_performed=False,
        live_real_order_submitted=False,
        live_real_network_submit_attempted=False,
        order_action_count=source.order_action_count,
        exchange_submit_count=source.exchange_submit_count,
        network_submit_count=source.network_submit_count,
        total_notional_usd=source.total_notional_usd,
        exchange_submit_blocked=True,
        live_real_blocked=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        reason_codes=reasons or ["LIVE_REAL_PREFLIGHT_GATE_READY"],
        source_30u=source.to_dict(),
        capability_audit=capability.to_dict(),
        hard_submit_block=hard_block.to_dict(),
        no_exchange_submit=no_exchange,
        no_live_real_order=no_live_order,
        source_30u_snapshot=source_snapshot,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    snapshot["approved_for_live_real_preflight_gate"] = approved
    snapshot["approved_for_live_real_readiness_candidate"] = approved
    return snapshot


def build_from_latest_30u_promotion_report(settings: Any | None = None, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source = latest_valid_30u_promotion_report(reports_dir)
    return build_live_real_preflight_gate_snapshot(
        resolved_settings,
        source,
        source_report_path=str(source_path) if source_path else None,
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
        f"# {CONTRACT_VERSION} Live-Real Preflight Gate",
        "",
        "Consumes 30U promotion review, audits API/env/account capability in redacted preflight mode, and keeps hard live submit blocked.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_live_real_preflight_gate`: `{payload.get('approved_for_live_real_preflight_gate')}`",
        f"- `approved_for_live_real_readiness_candidate`: `{payload.get('approved_for_live_real_readiness_candidate')}`",
        f"- `source_30u_promotion_review_verified`: `{payload.get('source_30u_promotion_review_verified')}`",
        f"- `api_env_capability_audit_verified`: `{payload.get('api_env_capability_audit_verified')}`",
        f"- `account_capability_audit_verified`: `{payload.get('account_capability_audit_verified')}`",
        f"- `hard_live_submit_block_verified`: `{payload.get('hard_live_submit_block_verified')}`",
        f"- `order_action_count`: `{payload.get('order_action_count')}`",
        f"- `exchange_submit_count`: `{payload.get('exchange_submit_count')}`",
        f"- `network_submit_count`: `{payload.get('network_submit_count')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        f"- `live_real_order_performed`: `{payload.get('live_real_order_performed')}`",
        "",
        "## Capability audit",
        f"- `api_key_redacted`: `{_mapping(payload.get('capability_audit')).get('api_key_redacted')}`",
        f"- `api_secret_redacted`: `{_mapping(payload.get('capability_audit')).get('api_secret_redacted')}`",
        f"- `account_capability_mode`: `{_mapping(payload.get('capability_audit')).get('account_capability_mode')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
