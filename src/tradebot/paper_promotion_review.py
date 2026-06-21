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

CONTRACT_VERSION = "4B.4.3.6.6.30U"
SOURCE_30T_CONTRACT_VERSION = "4B.4.3.6.6.30T"
SOURCE_30T_READY_DECISION = "PAPER_SOAK_EVIDENCE_WINDOW_READY_MULTI_CYCLE_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
REPORT_TYPE = "paper_promotion_review_risk_acceptance_gates_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630U_paper_promotion_review"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_PROMOTION_REVIEW_READY_RISK_ACCEPTANCE_GATES_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOURCE_30T_REQUIRED_DECISION = "PAPER_PROMOTION_REVIEW_30T_SOAK_EVIDENCE_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
RISK_GATES_NOT_READY_DECISION = "PAPER_PROMOTION_REVIEW_RISK_ACCEPTANCE_GATES_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_PROMOTION_REVIEW_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

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
class Source30TSoakStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    paper_soak_ready: bool
    source_30s_guardrail_verified: bool
    multi_cycle_soak_verified: bool
    cap_continuity_verified: bool
    kill_switch_continuity_verified: bool
    no_exchange_submit_verified: bool
    no_live_real_verified: bool
    soak_cycle_count: int
    minimum_soak_cycles_required: int
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    total_notional_usd: float
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
class RiskAcceptanceGate:
    name: str
    ok: bool
    required: bool
    reason_code: str
    observed: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RiskAcceptanceStatus:
    ok: bool
    required: bool
    total_gates: int
    passed_gates: int
    failed_gates: int
    gates: list[dict[str, Any]]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperPromotionReviewSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_paper_promotion_review: bool
    approved_for_paper_runtime_promotion_candidate: bool
    source_30t_soak_verified: bool
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
    minimum_soak_cycles_required: int
    total_notional_usd: float
    exchange_submit_blocked: bool
    live_real_blocked: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    reason_codes: list[str]
    source_30t: dict[str, Any]
    risk_acceptance: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30t_snapshot: dict[str, Any]

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
        "source_30t",
        "paper_soak_evidence_window",
        "multi_cycle_soak",
        "cap_continuity",
        "kill_switch_continuity",
        "no_exchange_submit",
        "no_live_real",
    ):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def evaluate_source_30t_soak(source_30t_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30TSoakStatus:
    nested = _nested(source_30t_snapshot)
    contract = str(source_30t_snapshot.get("contract_version") or "") or None
    decision = str(source_30t_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30T_READY_DECISION
    ready = _boolish(_first_present(source_30t_snapshot, ("approved_for_paper_soak_evidence_window",), nested.get("approved_for_paper_soak_evidence_window", decision_ok)), decision_ok)
    source_30s_ok = _boolish(_first_present(source_30t_snapshot, ("source_30s_guardrail_verified",), nested.get("source_30s_guardrail_verified", decision_ok)), decision_ok)
    soak_ok = _boolish(_first_present(source_30t_snapshot, ("multi_cycle_soak_verified",), nested.get("multi_cycle_soak_verified", decision_ok)), decision_ok)
    caps_ok = _boolish(_first_present(source_30t_snapshot, ("cap_continuity_verified",), nested.get("cap_continuity_verified", decision_ok)), decision_ok)
    kill_ok = _boolish(_first_present(source_30t_snapshot, ("kill_switch_continuity_verified",), nested.get("kill_switch_continuity_verified", decision_ok)), decision_ok)
    no_exchange = _boolish(_first_present(source_30t_snapshot, ("no_exchange_submit_verified",), nested.get("no_exchange_submit_verified", True)), True)
    no_live = _boolish(_first_present(source_30t_snapshot, ("no_live_real_verified",), nested.get("no_live_real_verified", True)), True)
    soak_cycles = _int(_first_present(source_30t_snapshot, ("soak_cycle_count",), nested.get("executed_cycles", 0)), 0)
    min_cycles = _int(_first_present(source_30t_snapshot, ("minimum_soak_cycles_required",), nested.get("min_cycles_required", 1)), 1)
    order_count = _int(_first_present(source_30t_snapshot, ("order_action_count",), nested.get("order_action_count", 0)), 0)
    exchange_count = _int(_first_present(source_30t_snapshot, ("exchange_submit_count",), nested.get("exchange_submit_count", 0)), 0)
    network_count = _int(_first_present(source_30t_snapshot, ("network_submit_count",), nested.get("network_submit_count", 0)), 0)
    notional = _float(_first_present(source_30t_snapshot, ("total_notional_usd",), nested.get("total_notional_usd", 0.0)), 0.0)
    approved_exchange = _boolish(source_30t_snapshot.get("approved_for_exchange_submit"), False)
    approved_live = _boolish(source_30t_snapshot.get("approved_for_live_real"), False)
    exchange_performed = _boolish(source_30t_snapshot.get("exchange_submit_performed"), False)
    network_attempted = _boolish(source_30t_snapshot.get("network_submit_attempted"), False)
    trading_action = _boolish(source_30t_snapshot.get("trading_action_performed"), False)
    order_actions = _boolish(source_30t_snapshot.get("order_actions_performed"), False)
    reasons: list[str] = []
    if contract != SOURCE_30T_CONTRACT_VERSION:
        reasons.append("SOURCE_30T_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30T_READY_SOAK_DECISION_REQUIRED")
    if not ready:
        reasons.append("SOURCE_30T_SOAK_NOT_READY")
    if not source_30s_ok or not soak_ok or not caps_ok or not kill_ok:
        reasons.append("SOURCE_30T_SOAK_COMPONENTS_NOT_VERIFIED")
    if soak_cycles < min_cycles:
        reasons.append("SOURCE_30T_MINIMUM_SOAK_CYCLES_REQUIRED")
    if not no_exchange or approved_exchange or exchange_performed or network_attempted:
        reasons.append("SOURCE_30T_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if not no_live or approved_live:
        reasons.append("SOURCE_30T_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions or order_count != 0 or exchange_count != 0 or network_count != 0:
        reasons.append("SOURCE_30T_TRADING_OR_SUBMIT_COUNTS_NOT_ZERO")
    if notional != 0.0:
        reasons.append("SOURCE_30T_NOTIONAL_MUST_REMAIN_ZERO")
    return Source30TSoakStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        paper_soak_ready=ready,
        source_30s_guardrail_verified=source_30s_ok,
        multi_cycle_soak_verified=soak_ok,
        cap_continuity_verified=caps_ok,
        kill_switch_continuity_verified=kill_ok,
        no_exchange_submit_verified=no_exchange,
        no_live_real_verified=no_live,
        soak_cycle_count=soak_cycles,
        minimum_soak_cycles_required=min_cycles,
        order_action_count=order_count,
        exchange_submit_count=exchange_count,
        network_submit_count=network_count,
        total_notional_usd=notional,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30T_PAPER_SOAK_EVIDENCE_VERIFIED"],
    )


def latest_valid_30t_soak_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    reports = Path(reports_dir)
    matches = sorted(
        [item for item in reports.glob("4B436630T_paper_soak_evidence_window_*_ready.json") if item.is_file()],
        key=lambda item: item.name,
        reverse=True,
    )
    for item in matches:
        try:
            payload = load_json(item)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and evaluate_source_30t_soak(payload, source_report_path=str(item)).ok:
            return item, payload
    return None, {}


def _gate(name: str, ok: bool, required: bool, reason_code: str, observed: Mapping[str, Any]) -> RiskAcceptanceGate:
    return RiskAcceptanceGate(name=name, ok=(ok or not required), required=required, reason_code=reason_code, observed=dict(observed))


def evaluate_risk_acceptance_gates(settings: Any, source: Source30TSoakStatus) -> RiskAcceptanceStatus:
    required = _boolish(_setting(settings, "paper_promotion_review_risk_acceptance_required", True), True)
    enabled = _boolish(_setting(settings, "paper_promotion_review_enabled", True), True)
    consume_30t_required = _boolish(_setting(settings, "paper_promotion_review_consume_30t_required", True), True)
    min_soak_cycles = max(1, _int(_setting(settings, "paper_promotion_review_min_soak_cycles_required", 3), 3))
    zero_counts_required = _boolish(_setting(settings, "paper_promotion_review_zero_action_counts_required", True), True)
    no_exchange_required = _boolish(_setting(settings, "paper_promotion_review_no_exchange_submit_required", True), True)
    no_live_required = _boolish(_setting(settings, "paper_promotion_review_no_live_real_required", True), True)
    caps_required = _boolish(_setting(settings, "paper_promotion_review_cap_continuity_required", True), True)
    kill_required = _boolish(_setting(settings, "paper_promotion_review_kill_switch_required", True), True)
    max_notional = max(0.0, _float(_setting(settings, "paper_promotion_review_max_total_notional_usd", 0.0), 0.0))
    gates = [
        _gate("promotion_review_enabled", enabled, required, "PAPER_PROMOTION_REVIEW_ENABLEMENT_REQUIRED", {"enabled": enabled}),
        _gate("consume_30t_soak", source.ok, consume_30t_required, "PAPER_PROMOTION_REVIEW_VALID_30T_SOAK_REQUIRED", {"source_ok": source.ok, "source_decision": source.source_decision}),
        _gate("minimum_soak_cycles", source.soak_cycle_count >= min_soak_cycles, required, "PAPER_PROMOTION_REVIEW_MINIMUM_SOAK_CYCLES_REQUIRED", {"soak_cycle_count": source.soak_cycle_count, "required": min_soak_cycles}),
        _gate("cap_continuity", source.cap_continuity_verified, caps_required, "PAPER_PROMOTION_REVIEW_CAP_CONTINUITY_REQUIRED", {"cap_continuity_verified": source.cap_continuity_verified}),
        _gate("kill_switch_continuity", source.kill_switch_continuity_verified, kill_required, "PAPER_PROMOTION_REVIEW_KILL_SWITCH_CONTINUITY_REQUIRED", {"kill_switch_continuity_verified": source.kill_switch_continuity_verified}),
        _gate("zero_action_counts", source.order_action_count == 0 and source.exchange_submit_count == 0 and source.network_submit_count == 0 and not source.trading_action_performed and not source.order_actions_performed, zero_counts_required, "PAPER_PROMOTION_REVIEW_ACTION_COUNTS_MUST_BE_ZERO", {"order_action_count": source.order_action_count, "exchange_submit_count": source.exchange_submit_count, "network_submit_count": source.network_submit_count}),
        _gate("zero_notional", source.total_notional_usd <= max_notional, required, "PAPER_PROMOTION_REVIEW_TOTAL_NOTIONAL_MUST_REMAIN_ZERO", {"total_notional_usd": source.total_notional_usd, "max_total_notional_usd": max_notional}),
        _gate("no_exchange_submit", source.no_exchange_submit_verified and not source.approved_for_exchange_submit and not source.exchange_submit_performed and not source.network_submit_attempted, no_exchange_required, "PAPER_PROMOTION_REVIEW_NO_EXCHANGE_SUBMIT_REQUIRED", {"approved_for_exchange_submit": source.approved_for_exchange_submit, "exchange_submit_performed": source.exchange_submit_performed, "network_submit_attempted": source.network_submit_attempted}),
        _gate("no_live_real", source.no_live_real_verified and not source.approved_for_live_real, no_live_required, "PAPER_PROMOTION_REVIEW_NO_LIVE_REAL_REQUIRED", {"approved_for_live_real": source.approved_for_live_real, "no_live_real_verified": source.no_live_real_verified}),
    ]
    gate_dicts = [gate.to_dict() for gate in gates]
    failed = [gate for gate in gates if not gate.ok]
    return RiskAcceptanceStatus(
        ok=not failed,
        required=required,
        total_gates=len(gates),
        passed_gates=len(gates) - len(failed),
        failed_gates=len(failed),
        gates=gate_dicts,
        reason_codes=[gate.reason_code for gate in failed] or ["PAPER_PROMOTION_REVIEW_RISK_ACCEPTANCE_GATES_VERIFIED"],
    )


def build_paper_promotion_review_snapshot(
    settings: Any | None = None,
    source_30t_snapshot: Mapping[str, Any] | None = None,
    *,
    source_report_path: str | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_snapshot = dict(_mapping(source_30t_snapshot))
    source = evaluate_source_30t_soak(source_snapshot, source_report_path=source_report_path)
    risk_acceptance = evaluate_risk_acceptance_gates(resolved_settings, source)
    no_exchange = {
        "ok": source.ok and risk_acceptance.ok and source.no_exchange_submit_verified and not source.approved_for_exchange_submit and not source.exchange_submit_performed and not source.network_submit_attempted,
        "required": _boolish(_setting(resolved_settings, "paper_promotion_review_no_exchange_submit_required", True), True),
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_submit_count": source.exchange_submit_count,
        "network_submit_count": source.network_submit_count,
        "reason_codes": ["PAPER_PROMOTION_REVIEW_NO_EXCHANGE_SUBMIT_VERIFIED"],
    }
    no_live = {
        "ok": source.ok and risk_acceptance.ok and source.no_live_real_verified and not source.approved_for_live_real,
        "required": _boolish(_setting(resolved_settings, "paper_promotion_review_no_live_real_required", True), True),
        "approved_for_live_real": False,
        "reason_codes": ["PAPER_PROMOTION_REVIEW_NO_LIVE_REAL_VERIFIED"],
    }
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not risk_acceptance.ok:
        reasons.extend(risk_acceptance.reason_codes)
    if not no_exchange["ok"]:
        reasons.extend(no_exchange["reason_codes"])
    if not no_live["ok"]:
        reasons.extend(no_live["reason_codes"])
    if source.ok and risk_acceptance.ok and no_exchange["ok"] and no_live["ok"]:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30T_REQUIRED_DECISION
    elif not risk_acceptance.ok:
        decision = RISK_GATES_NOT_READY_DECISION
    else:
        decision = NOT_READY_DECISION
    approved = decision == READY_DECISION
    snapshot = PaperPromotionReviewSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_30T_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_paper_promotion_review=approved,
        approved_for_paper_runtime_promotion_candidate=approved,
        source_30t_soak_verified=source.ok,
        risk_acceptance_gates_verified=risk_acceptance.ok,
        promotion_readiness_review_verified=approved,
        no_exchange_submit_verified=bool(no_exchange["ok"]),
        no_live_real_verified=bool(no_live["ok"]),
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        exchange_submit_performed=False,
        network_submit_attempted=False,
        trading_action_performed=False,
        order_actions_performed=False,
        order_action_count=source.order_action_count,
        exchange_submit_count=source.exchange_submit_count,
        network_submit_count=source.network_submit_count,
        soak_cycle_count=source.soak_cycle_count,
        minimum_soak_cycles_required=source.minimum_soak_cycles_required,
        total_notional_usd=source.total_notional_usd,
        exchange_submit_blocked=True,
        live_real_blocked=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        reason_codes=reasons or ["PAPER_PROMOTION_REVIEW_READY"],
        source_30t=source.to_dict(),
        risk_acceptance=risk_acceptance.to_dict(),
        no_exchange_submit=no_exchange,
        no_live_real=no_live,
        source_30t_snapshot=source_snapshot,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    snapshot["approved_for_paper_promotion_review"] = approved
    snapshot["approved_for_paper_runtime_promotion_candidate"] = approved
    return snapshot


def build_from_latest_30t_soak_report(settings: Any | None = None, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source = latest_valid_30t_soak_report(reports_dir)
    return build_paper_promotion_review_snapshot(
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
        f"# {CONTRACT_VERSION} Paper Promotion Review",
        "",
        "Consumes 30T paper soak evidence, verifies promotion readiness and risk acceptance gates, and keeps exchange submit/live-real blocked.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_paper_promotion_review`: `{payload.get('approved_for_paper_promotion_review')}`",
        f"- `approved_for_paper_runtime_promotion_candidate`: `{payload.get('approved_for_paper_runtime_promotion_candidate')}`",
        f"- `source_30t_soak_verified`: `{payload.get('source_30t_soak_verified')}`",
        f"- `risk_acceptance_gates_verified`: `{payload.get('risk_acceptance_gates_verified')}`",
        f"- `promotion_readiness_review_verified`: `{payload.get('promotion_readiness_review_verified')}`",
        f"- `soak_cycle_count`: `{payload.get('soak_cycle_count')}`",
        f"- `minimum_soak_cycles_required`: `{payload.get('minimum_soak_cycles_required')}`",
        f"- `order_action_count`: `{payload.get('order_action_count')}`",
        f"- `exchange_submit_count`: `{payload.get('exchange_submit_count')}`",
        f"- `network_submit_count`: `{payload.get('network_submit_count')}`",
        f"- `approved_for_exchange_submit`: `{payload.get('approved_for_exchange_submit')}`",
        f"- `approved_for_live_real`: `{payload.get('approved_for_live_real')}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
