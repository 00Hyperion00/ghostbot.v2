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

CONTRACT_VERSION = "4B.4.3.6.6.30W"
SOURCE_30V_CONTRACT_VERSION = "4B.4.3.6.6.30V"
SOURCE_30V_READY_DECISION = "LIVE_REAL_PREFLIGHT_GATE_READY_API_ENV_ACCOUNT_AUDIT_HARD_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER"
REPORT_TYPE = "live_real_final_operator_approval_hard_submit_blocked_no_live_real_order"
REPORT_PREFIX = "4B436630W_live_real_final_operator_approval"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

APPROVAL_TOKEN = "APPROVE_LIVE_REAL_FINAL_OPERATOR_APPROVAL"
READY_DECISION = "LIVE_REAL_FINAL_OPERATOR_APPROVAL_READY_FINAL_APPROVAL_CAPTURED_SUBMIT_BLOCKED_UNTIL_30X_NO_LIVE_REAL_ORDER"
OPERATOR_APPROVAL_REQUIRED_DECISION = "LIVE_REAL_FINAL_OPERATOR_APPROVAL_OPERATOR_APPROVAL_REQUIRED_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER"
SOURCE_30V_REQUIRED_DECISION = "LIVE_REAL_FINAL_OPERATOR_APPROVAL_30V_PREFLIGHT_REQUIRED_NO_LIVE_REAL_ORDER"
HARD_BLOCK_NOT_READY_DECISION = "LIVE_REAL_FINAL_OPERATOR_APPROVAL_HARD_SUBMIT_BLOCK_NOT_READY_NO_LIVE_REAL_ORDER"
NOT_READY_DECISION = "LIVE_REAL_FINAL_OPERATOR_APPROVAL_NOT_READY_NO_LIVE_REAL_ORDER"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "preflight_only": True,
    "operator_approval_only": True,
    "live_real_final_approval_only": True,
    "exchange_submit_path_guarded": True,
    "exchange_submit_blocked": True,
    "live_real_blocked": True,
    "live_real_submit_blocked_until_30x": True,
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
class Source30VPreflightStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    live_real_preflight_ready: bool
    live_real_readiness_candidate: bool
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
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorApprovalStatus:
    ok: bool
    required: bool
    issued: bool
    operator_id: str | None
    approval_token_expected: str
    approval_token_matched: bool
    final_operator_id_required: bool
    captured_at_utc: str | None
    no_secret_material_persisted: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FinalHardSubmitBlockStatus:
    ok: bool
    required: bool
    submit_blocked_until_30x: bool
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
class LiveRealFinalOperatorApprovalSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_live_real_final_operator_approval: bool
    approved_for_30x_live_real_micro_canary_candidate: bool
    source_30v_live_real_preflight_verified: bool
    final_operator_approval_verified: bool
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
    live_real_submit_blocked_until_30x: bool
    runtime_activation_blocked: bool
    training_reload_blocked: bool
    reason_codes: list[str]
    source_30v: dict[str, Any]
    operator_approval: dict[str, Any]
    hard_submit_block: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real_order: dict[str, Any]
    source_30v_snapshot: dict[str, Any]

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
        "source_30v",
        "live_real_preflight",
        "capability_audit",
        "hard_submit_block",
        "no_exchange_submit",
        "no_live_real_order",
    ):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def evaluate_source_30v_preflight(source_30v_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30VPreflightStatus:
    nested = _nested(source_30v_snapshot)
    contract = str(source_30v_snapshot.get("contract_version") or "") or None
    decision = str(source_30v_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30V_READY_DECISION
    preflight_ready = _boolish(_first_present(source_30v_snapshot, ("approved_for_live_real_preflight_gate",), nested.get("approved_for_live_real_preflight_gate", decision_ok)), decision_ok)
    readiness_candidate = _boolish(_first_present(source_30v_snapshot, ("approved_for_live_real_readiness_candidate",), nested.get("approved_for_live_real_readiness_candidate", decision_ok)), decision_ok)
    api_env_ok = _boolish(_first_present(source_30v_snapshot, ("api_env_capability_audit_verified",), nested.get("api_env_capability_audit_verified", decision_ok)), decision_ok)
    account_ok = _boolish(_first_present(source_30v_snapshot, ("account_capability_audit_verified",), nested.get("account_capability_audit_verified", decision_ok)), decision_ok)
    hard_block_ok = _boolish(_first_present(source_30v_snapshot, ("hard_live_submit_block_verified",), nested.get("hard_live_submit_block_verified", decision_ok)), decision_ok)
    no_exchange = _boolish(_first_present(source_30v_snapshot, ("no_exchange_submit_verified",), nested.get("no_exchange_submit_verified", True)), True)
    no_live_order = _boolish(_first_present(source_30v_snapshot, ("no_live_real_order_verified",), nested.get("no_live_real_order_verified", True)), True)
    approved_exchange = _boolish(source_30v_snapshot.get("approved_for_exchange_submit"), False)
    approved_live = _boolish(source_30v_snapshot.get("approved_for_live_real"), False)
    exchange_performed = _boolish(source_30v_snapshot.get("exchange_submit_performed"), False)
    network_attempted = _boolish(source_30v_snapshot.get("network_submit_attempted"), False)
    trading_action = _boolish(source_30v_snapshot.get("trading_action_performed"), False)
    order_actions = _boolish(source_30v_snapshot.get("order_actions_performed"), False)
    live_order = _boolish(source_30v_snapshot.get("live_real_order_performed"), False)
    live_submitted = _boolish(source_30v_snapshot.get("live_real_order_submitted"), False)
    live_network = _boolish(source_30v_snapshot.get("live_real_network_submit_attempted"), False)
    order_count = _int(_first_present(source_30v_snapshot, ("order_action_count",), nested.get("order_action_count", 0)), 0)
    exchange_count = _int(_first_present(source_30v_snapshot, ("exchange_submit_count",), nested.get("exchange_submit_count", 0)), 0)
    network_count = _int(_first_present(source_30v_snapshot, ("network_submit_count",), nested.get("network_submit_count", 0)), 0)
    notional = _float(_first_present(source_30v_snapshot, ("total_notional_usd",), nested.get("total_notional_usd", 0.0)), 0.0)
    reasons: list[str] = []
    if contract != SOURCE_30V_CONTRACT_VERSION:
        reasons.append("SOURCE_30V_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30V_READY_PREFLIGHT_DECISION_REQUIRED")
    if not preflight_ready or not readiness_candidate:
        reasons.append("SOURCE_30V_PREFLIGHT_NOT_READY")
    if not api_env_ok or not account_ok:
        reasons.append("SOURCE_30V_API_ENV_ACCOUNT_AUDIT_NOT_VERIFIED")
    if not hard_block_ok:
        reasons.append("SOURCE_30V_HARD_SUBMIT_BLOCK_NOT_VERIFIED")
    if not no_exchange or approved_exchange or exchange_performed or network_attempted:
        reasons.append("SOURCE_30V_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if not no_live_order or approved_live or live_order or live_submitted or live_network:
        reasons.append("SOURCE_30V_LIVE_REAL_ORDER_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if trading_action or order_actions or order_count != 0 or exchange_count != 0 or network_count != 0:
        reasons.append("SOURCE_30V_TRADING_OR_SUBMIT_COUNTS_NOT_ZERO")
    if notional != 0.0:
        reasons.append("SOURCE_30V_NOTIONAL_MUST_REMAIN_ZERO")
    return Source30VPreflightStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        live_real_preflight_ready=preflight_ready,
        live_real_readiness_candidate=readiness_candidate,
        api_env_capability_audit_verified=api_env_ok,
        account_capability_audit_verified=account_ok,
        hard_live_submit_block_verified=hard_block_ok,
        no_exchange_submit_verified=no_exchange,
        no_live_real_order_verified=no_live_order,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        live_real_order_performed=live_order,
        live_real_order_submitted=live_submitted,
        live_real_network_submit_attempted=live_network,
        order_action_count=order_count,
        exchange_submit_count=exchange_count,
        network_submit_count=network_count,
        total_notional_usd=notional,
        reason_codes=reasons or ["SOURCE_30V_LIVE_REAL_PREFLIGHT_VERIFIED"],
    )


def latest_valid_30v_preflight_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    reports = Path(reports_dir)
    matches = sorted(
        [item for item in reports.glob("4B436630V_live_real_preflight_gate_*_ready.json") if item.is_file()],
        key=lambda item: item.name,
        reverse=True,
    )
    for item in matches:
        try:
            payload = load_json(item)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and evaluate_source_30v_preflight(payload, source_report_path=str(item)).ok:
            return item, payload
    return None, {}


def evaluate_operator_approval(
    settings: Any,
    *,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_final_approval: bool = False,
) -> OperatorApprovalStatus:
    required = _boolish(_setting(settings, "live_real_final_operator_approval_required", True), True)
    id_required = _boolish(_setting(settings, "live_real_final_operator_id_required", True), True)
    expected = str(_setting(settings, "live_real_final_operator_approval_token", APPROVAL_TOKEN) or APPROVAL_TOKEN)
    clean_operator_id = str(operator_id).strip() if operator_id is not None else ""
    clean_token = str(approval_token).strip() if approval_token is not None else ""
    token_ok = issue_final_approval and clean_token == expected
    operator_ok = bool(clean_operator_id) if id_required else True
    ok = required and token_ok and operator_ok
    reasons: list[str] = []
    if not required:
        reasons.append("LIVE_REAL_FINAL_OPERATOR_APPROVAL_REQUIRED")
    if not issue_final_approval:
        reasons.append("LIVE_REAL_FINAL_OPERATOR_APPROVAL_FLAG_REQUIRED")
    if not token_ok:
        reasons.append("LIVE_REAL_FINAL_OPERATOR_APPROVAL_TOKEN_MISMATCH")
    if not operator_ok:
        reasons.append("LIVE_REAL_FINAL_OPERATOR_ID_REQUIRED")
    return OperatorApprovalStatus(
        ok=ok,
        required=required,
        issued=issue_final_approval,
        operator_id=clean_operator_id or None,
        approval_token_expected=expected,
        approval_token_matched=token_ok,
        final_operator_id_required=id_required,
        captured_at_utc=utc_now_iso() if ok else None,
        no_secret_material_persisted=True,
        reason_codes=reasons or ["LIVE_REAL_FINAL_OPERATOR_APPROVAL_VERIFIED"],
    )


def evaluate_final_hard_submit_block(settings: Any, source: Source30VPreflightStatus) -> FinalHardSubmitBlockStatus:
    required = _boolish(_setting(settings, "live_real_final_hard_submit_block_required", True), True)
    no_live_order_required = _boolish(_setting(settings, "live_real_final_no_live_order_required", True), True)
    submit_blocked_until_30x = _boolish(_setting(settings, "live_real_final_submit_blocked_until_30x", True), True)
    exchange_cap = max(0, _int(_setting(settings, "live_real_final_exchange_submit_cap", 0), 0))
    network_cap = max(0, _int(_setting(settings, "live_real_final_network_submit_cap", 0), 0))
    order_cap = max(0, _int(_setting(settings, "live_real_final_order_action_cap", 0), 0))
    ok = (
        required
        and no_live_order_required
        and submit_blocked_until_30x
        and not source.approved_for_exchange_submit
        and not source.approved_for_live_real
        and not source.exchange_submit_performed
        and not source.network_submit_attempted
        and not source.trading_action_performed
        and not source.order_actions_performed
        and not source.live_real_order_performed
        and not source.live_real_order_submitted
        and not source.live_real_network_submit_attempted
        and source.exchange_submit_count <= exchange_cap
        and source.network_submit_count <= network_cap
        and source.order_action_count <= order_cap
    )
    reasons: list[str] = []
    if not required:
        reasons.append("LIVE_REAL_FINAL_HARD_SUBMIT_BLOCK_REQUIRED")
    if not no_live_order_required:
        reasons.append("LIVE_REAL_FINAL_NO_LIVE_ORDER_REQUIRED")
    if not submit_blocked_until_30x:
        reasons.append("LIVE_REAL_FINAL_SUBMIT_BLOCKED_UNTIL_30X_REQUIRED")
    if not ok and not reasons:
        reasons.append("LIVE_REAL_FINAL_SOURCE_SUBMIT_OR_ORDER_ACTIVITY_NOT_ZERO")
    return FinalHardSubmitBlockStatus(
        ok=ok,
        required=required,
        submit_blocked_until_30x=submit_blocked_until_30x,
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
        reason_codes=reasons or ["LIVE_REAL_FINAL_HARD_SUBMIT_BLOCK_VERIFIED_UNTIL_30X"],
    )


def build_live_real_final_operator_approval_snapshot(
    settings: Any | None = None,
    source_30v_snapshot: Mapping[str, Any] | None = None,
    *,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_final_approval: bool = False,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_snapshot = dict(_mapping(source_30v_snapshot))
    source = evaluate_source_30v_preflight(source_snapshot, source_report_path=source_report_path)
    operator = evaluate_operator_approval(
        resolved_settings,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_final_approval=issue_final_approval,
    )
    hard_block = evaluate_final_hard_submit_block(resolved_settings, source)
    no_exchange = {
        "ok": source.ok and hard_block.ok and not hard_block.approved_for_exchange_submit and not hard_block.exchange_submit_performed and not hard_block.network_submit_attempted,
        "required": True,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_submit_count": hard_block.exchange_submit_count,
        "network_submit_count": hard_block.network_submit_count,
        "reason_codes": ["LIVE_REAL_FINAL_NO_EXCHANGE_SUBMIT_VERIFIED"],
    }
    no_live_order = {
        "ok": source.ok and hard_block.ok and not hard_block.approved_for_live_real and not hard_block.live_real_order_performed and not hard_block.live_real_order_submitted and not hard_block.live_real_network_submit_attempted,
        "required": True,
        "approved_for_live_real": False,
        "live_real_order_performed": False,
        "live_real_order_submitted": False,
        "live_real_network_submit_attempted": False,
        "reason_codes": ["LIVE_REAL_FINAL_NO_LIVE_REAL_ORDER_VERIFIED"],
    }
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not operator.ok:
        reasons.extend(operator.reason_codes)
    if not hard_block.ok:
        reasons.extend(hard_block.reason_codes)
    if not no_exchange["ok"]:
        reasons.extend(no_exchange["reason_codes"])
    if not no_live_order["ok"]:
        reasons.extend(no_live_order["reason_codes"])
    if source.ok and operator.ok and hard_block.ok and no_exchange["ok"] and no_live_order["ok"]:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30V_REQUIRED_DECISION
    elif not operator.ok:
        decision = OPERATOR_APPROVAL_REQUIRED_DECISION
    elif not hard_block.ok:
        decision = HARD_BLOCK_NOT_READY_DECISION
    else:
        decision = NOT_READY_DECISION
    approved = decision == READY_DECISION
    snapshot = LiveRealFinalOperatorApprovalSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_30V_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_live_real_final_operator_approval=approved,
        approved_for_30x_live_real_micro_canary_candidate=approved,
        source_30v_live_real_preflight_verified=source.ok,
        final_operator_approval_verified=operator.ok,
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
        live_real_submit_blocked_until_30x=True,
        runtime_activation_blocked=True,
        training_reload_blocked=True,
        reason_codes=reasons or ["LIVE_REAL_FINAL_OPERATOR_APPROVAL_READY_SUBMIT_BLOCKED_UNTIL_30X"],
        source_30v=source.to_dict(),
        operator_approval=operator.to_dict(),
        hard_submit_block=hard_block.to_dict(),
        no_exchange_submit=no_exchange,
        no_live_real_order=no_live_order,
        source_30v_snapshot=source_snapshot,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    snapshot["approved_for_live_real_final_operator_approval"] = approved
    snapshot["approved_for_30x_live_real_micro_canary_candidate"] = approved
    return snapshot


def build_from_latest_30v_preflight_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    approval_token: str | None = None,
    issue_final_approval: bool = False,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source = latest_valid_30v_preflight_report(reports_dir)
    return build_live_real_final_operator_approval_snapshot(
        resolved_settings,
        source,
        source_report_path=str(source_path) if source_path else None,
        operator_id=operator_id,
        approval_token=approval_token,
        issue_final_approval=issue_final_approval,
    )


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "approval_required" if payload.get("decision") == OPERATOR_APPROVAL_REQUIRED_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    write_json_atomic(json_path, payload)
    operator = _mapping(payload.get("operator_approval"))
    lines = [
        f"# {CONTRACT_VERSION} Live-Real Final Operator Approval",
        "",
        "Consumes 30V live-real preflight, captures explicit final operator approval, and keeps live-real submit blocked until 30X.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_live_real_final_operator_approval`: `{payload.get('approved_for_live_real_final_operator_approval')}`",
        f"- `approved_for_30x_live_real_micro_canary_candidate`: `{payload.get('approved_for_30x_live_real_micro_canary_candidate')}`",
        f"- `source_30v_live_real_preflight_verified`: `{payload.get('source_30v_live_real_preflight_verified')}`",
        f"- `final_operator_approval_verified`: `{payload.get('final_operator_approval_verified')}`",
        f"- `hard_live_submit_block_verified`: `{payload.get('hard_live_submit_block_verified')}`",
        f"- `live_real_submit_blocked_until_30x`: `{payload.get('live_real_submit_blocked_until_30x')}`",
        f"- `order_action_count`: `{payload.get('order_action_count')}`",
        f"- `exchange_submit_count`: `{payload.get('exchange_submit_count')}`",
        f"- `network_submit_count`: `{payload.get('network_submit_count')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        f"- `live_real_order_performed`: `{payload.get('live_real_order_performed')}`",
        "",
        "## Operator approval",
        f"- `operator_id`: `{operator.get('operator_id')}`",
        f"- `approval_token_matched`: `{operator.get('approval_token_matched')}`",
        f"- `captured_at_utc`: `{operator.get('captured_at_utc')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
