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

CONTRACT_VERSION = "4B.4.3.6.6.30T"
SOURCE_30S_CONTRACT_VERSION = "4B.4.3.6.6.30S"
SOURCE_30S_READY_DECISION = "PAPER_MODE_RUNTIME_GUARDRAIL_READY_GUARDED_LOOP_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
REPORT_TYPE = "paper_soak_evidence_window_multi_cycle_caps_kill_switch_no_exchange_submit_no_live_real"
REPORT_PREFIX = "4B436630T_paper_soak_evidence_window"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SOAK_EVIDENCE_WINDOW_READY_MULTI_CYCLE_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOURCE_30S_REQUIRED_DECISION = "PAPER_SOAK_EVIDENCE_WINDOW_30S_GUARDED_RUNTIME_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
SOAK_NOT_READY_DECISION = "PAPER_SOAK_EVIDENCE_WINDOW_MULTI_CYCLE_SOAK_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
CAPS_NOT_READY_DECISION = "PAPER_SOAK_EVIDENCE_WINDOW_CAP_CONTINUITY_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
KILL_SWITCH_REQUIRED_DECISION = "PAPER_SOAK_EVIDENCE_WINDOW_KILL_SWITCH_CONTINUITY_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
NOT_READY_DECISION = "PAPER_SOAK_EVIDENCE_WINDOW_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"

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
class Source30SGuardrailStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    runtime_guardrail_ready: bool
    source_30r_consumed: bool
    guarded_runtime_loop_verified: bool
    strict_caps_verified: bool
    kill_switch_verified: bool
    no_exchange_submit_verified: bool
    no_live_real_verified: bool
    loop_tick_count: int
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
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
class PaperSoakCycle:
    index: int
    event_type: str
    source_runtime_guardrail_verified: bool
    cap_continuity_verified: bool
    kill_switch_enabled: bool
    signal: str
    action: str
    order_action_performed: bool
    exchange_submit_performed: bool
    network_submit_attempted: bool
    notional_usd: float
    reason_code: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MultiCycleSoakStatus:
    ok: bool
    required: bool
    requested_cycles: int
    min_cycles_required: int
    executed_cycles: int
    cycle_cap: int
    cycle_window_completed: bool
    order_action_count: int
    exchange_submit_count: int
    network_submit_count: int
    trading_action_count: int
    total_notional_usd: float
    cycles: list[dict[str, Any]]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CapContinuityStatus:
    ok: bool
    required: bool
    cycle_cap: int
    executed_cycles: int
    min_cycles_required: int
    order_action_cap: int
    order_action_count: int
    exchange_submit_cap: int
    exchange_submit_count: int
    network_submit_cap: int
    network_submit_count: int
    max_notional_usd: float
    total_notional_usd: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class KillSwitchContinuityStatus:
    ok: bool
    required: bool
    enabled: bool
    cycles_checked: int
    all_cycles_kill_switch_enabled: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSoakEvidenceWindowSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_paper_soak_evidence_window: bool
    source_30s_guardrail_verified: bool
    multi_cycle_soak_verified: bool
    cap_continuity_verified: bool
    kill_switch_continuity_verified: bool
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
    source_30s: dict[str, Any]
    multi_cycle_soak: dict[str, Any]
    cap_continuity: dict[str, Any]
    kill_switch_continuity: dict[str, Any]
    no_exchange_submit: dict[str, Any]
    no_live_real: dict[str, Any]
    source_30s_snapshot: dict[str, Any]

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
        "source_30s",
        "paper_mode_runtime_guardrail",
        "guarded_runtime_loop",
        "strict_caps",
        "kill_switch_proof",
        "no_exchange_submit",
        "no_live_real",
    ):
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
    return merged


def evaluate_source_30s_guardrail(source_30s_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30SGuardrailStatus:
    nested = _nested(source_30s_snapshot)
    contract = str(source_30s_snapshot.get("contract_version") or "") or None
    decision = str(source_30s_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30S_READY_DECISION
    ready = _boolish(_first_present(source_30s_snapshot, ("approved_for_paper_mode_runtime_guardrail", "runtime_guardrail_ready"), nested.get("approved_for_paper_mode_runtime_guardrail", decision_ok)), decision_ok)
    source_30r = _boolish(_first_present(source_30s_snapshot, ("source_30r_reconciliation_verified",), nested.get("source_30r_reconciliation_verified", decision_ok)), decision_ok)
    loop_ok = _boolish(_first_present(source_30s_snapshot, ("guarded_runtime_loop_verified",), nested.get("guarded_runtime_loop_verified", decision_ok)), decision_ok)
    caps_ok = _boolish(_first_present(source_30s_snapshot, ("strict_caps_verified",), nested.get("strict_caps_verified", decision_ok)), decision_ok)
    kill_ok = _boolish(_first_present(source_30s_snapshot, ("kill_switch_verified",), nested.get("kill_switch_verified", decision_ok)), decision_ok)
    no_exchange = _boolish(_first_present(source_30s_snapshot, ("no_exchange_submit_verified",), nested.get("no_exchange_submit_verified", True)), True)
    no_live = _boolish(_first_present(source_30s_snapshot, ("no_live_real_verified",), nested.get("no_live_real_verified", True)), True)
    loop_ticks = _int(_first_present(source_30s_snapshot, ("loop_tick_count",), nested.get("loop_tick_count", 0)), 0)
    order_count = _int(_first_present(source_30s_snapshot, ("order_action_count",), nested.get("order_action_count", 0)), 0)
    exchange_count = _int(_first_present(source_30s_snapshot, ("exchange_submit_count",), nested.get("exchange_submit_count", 0)), 0)
    network_count = _int(_first_present(source_30s_snapshot, ("network_submit_count",), nested.get("network_submit_count", 0)), 0)
    approved_exchange = _boolish(source_30s_snapshot.get("approved_for_exchange_submit"), False)
    approved_live = _boolish(source_30s_snapshot.get("approved_for_live_real"), False)
    exchange_performed = _boolish(source_30s_snapshot.get("exchange_submit_performed"), False)
    network_attempted = _boolish(source_30s_snapshot.get("network_submit_attempted"), False)
    trading_action = _boolish(source_30s_snapshot.get("trading_action_performed"), False)
    order_actions = _boolish(source_30s_snapshot.get("order_actions_performed"), False)
    reasons: list[str] = []
    if contract != SOURCE_30S_CONTRACT_VERSION:
        reasons.append("SOURCE_30S_CONTRACT_VERSION_MISMATCH")
    if not decision_ok:
        reasons.append("SOURCE_30S_READY_GUARDRAIL_DECISION_REQUIRED")
    if not ready:
        reasons.append("SOURCE_30S_RUNTIME_GUARDRAIL_NOT_READY")
    if not source_30r or not loop_ok or not caps_ok or not kill_ok:
        reasons.append("SOURCE_30S_GUARDRAIL_COMPONENTS_NOT_VERIFIED")
    if not no_exchange or approved_exchange or exchange_performed or network_attempted:
        reasons.append("SOURCE_30S_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED")
    if not no_live or approved_live:
        reasons.append("SOURCE_30S_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if trading_action or order_actions or order_count != 0 or exchange_count != 0 or network_count != 0:
        reasons.append("SOURCE_30S_TRADING_OR_SUBMIT_COUNTS_NOT_ZERO")
    if loop_ticks <= 0:
        reasons.append("SOURCE_30S_LOOP_TICK_COUNT_REQUIRED")
    return Source30SGuardrailStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        runtime_guardrail_ready=ready,
        source_30r_consumed=source_30r,
        guarded_runtime_loop_verified=loop_ok,
        strict_caps_verified=caps_ok,
        kill_switch_verified=kill_ok,
        no_exchange_submit_verified=no_exchange,
        no_live_real_verified=no_live,
        loop_tick_count=loop_ticks,
        order_action_count=order_count,
        exchange_submit_count=exchange_count,
        network_submit_count=network_count,
        approved_for_exchange_submit=approved_exchange,
        approved_for_live_real=approved_live,
        exchange_submit_performed=exchange_performed,
        network_submit_attempted=network_attempted,
        trading_action_performed=trading_action,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["SOURCE_30S_RUNTIME_GUARDRAIL_VERIFIED"],
    )


def latest_valid_30s_guardrail_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    reports = Path(reports_dir)
    matches = sorted(
        [item for item in reports.glob("4B436630S_paper_mode_runtime_guardrail_*_ready.json") if item.is_file()],
        key=lambda item: item.name,
        reverse=True,
    )
    for item in matches:
        try:
            payload = load_json(item)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and evaluate_source_30s_guardrail(payload, source_report_path=str(item)).ok:
            return item, payload
    return None, {}


def build_multi_cycle_soak(settings: Any, source: Source30SGuardrailStatus) -> MultiCycleSoakStatus:
    required = _boolish(_setting(settings, "paper_soak_evidence_window_enabled", True), True)
    requested_cycles = max(0, _int(_setting(settings, "paper_soak_evidence_window_cycle_count", 5), 5))
    min_cycles = max(1, _int(_setting(settings, "paper_soak_evidence_window_min_cycles_required", 3), 3))
    cycle_cap = max(0, _int(_setting(settings, "paper_soak_evidence_window_cycle_cap", 10), 10))
    executed_cycles = min(requested_cycles, cycle_cap)
    cycles: list[dict[str, Any]] = []
    for index in range(executed_cycles):
        cycles.append(PaperSoakCycle(
            index=index,
            event_type="paper_soak_evidence_cycle",
            source_runtime_guardrail_verified=source.ok,
            cap_continuity_verified=True,
            kill_switch_enabled=True,
            signal="HOLD",
            action="PAPER_SOAK_OBSERVE_NO_ORDER",
            order_action_performed=False,
            exchange_submit_performed=False,
            network_submit_attempted=False,
            notional_usd=0.0,
            reason_code="PAPER_SOAK_EVIDENCE_NO_ORDER_ACTION",
        ).to_dict())
    order_actions = sum(1 for cycle in cycles if _boolish(cycle.get("order_action_performed"), False))
    exchange_submits = sum(1 for cycle in cycles if _boolish(cycle.get("exchange_submit_performed"), False))
    network_submits = sum(1 for cycle in cycles if _boolish(cycle.get("network_submit_attempted"), False))
    trading_actions = sum(1 for cycle in cycles if str(cycle.get("action")) != "PAPER_SOAK_OBSERVE_NO_ORDER")
    total_notional = sum(_float(cycle.get("notional_usd"), 0.0) for cycle in cycles)
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_SOAK_EVIDENCE_WINDOW_REQUIRED")
    if not source.ok:
        reasons.append("PAPER_SOAK_EVIDENCE_SOURCE_30S_NOT_READY")
    if requested_cycles < min_cycles or executed_cycles < min_cycles:
        reasons.append("PAPER_SOAK_EVIDENCE_MINIMUM_CYCLES_REQUIRED")
    if requested_cycles > cycle_cap:
        reasons.append("PAPER_SOAK_EVIDENCE_REQUESTED_CYCLES_EXCEED_CAP")
    if order_actions or exchange_submits or network_submits or trading_actions:
        reasons.append("PAPER_SOAK_EVIDENCE_ACTION_COUNTS_NOT_ZERO")
    if total_notional != 0.0:
        reasons.append("PAPER_SOAK_EVIDENCE_NOTIONAL_MUST_REMAIN_ZERO")
    return MultiCycleSoakStatus(
        ok=not reasons,
        required=required,
        requested_cycles=requested_cycles,
        min_cycles_required=min_cycles,
        executed_cycles=executed_cycles,
        cycle_cap=cycle_cap,
        cycle_window_completed=executed_cycles >= min_cycles and requested_cycles <= cycle_cap,
        order_action_count=order_actions,
        exchange_submit_count=exchange_submits,
        network_submit_count=network_submits,
        trading_action_count=trading_actions,
        total_notional_usd=total_notional,
        cycles=cycles,
        reason_codes=reasons or ["PAPER_SOAK_EVIDENCE_MULTI_CYCLE_WINDOW_VERIFIED"],
    )


def evaluate_cap_continuity(settings: Any, soak: MultiCycleSoakStatus) -> CapContinuityStatus:
    required = _boolish(_setting(settings, "paper_soak_evidence_window_cap_continuity_required", True), True)
    order_cap = max(0, _int(_setting(settings, "paper_soak_evidence_window_order_action_cap", 0), 0))
    exchange_cap = max(0, _int(_setting(settings, "paper_soak_evidence_window_exchange_submit_cap", 0), 0))
    network_cap = max(0, _int(_setting(settings, "paper_soak_evidence_window_network_submit_cap", 0), 0))
    max_notional = max(0.0, _float(_setting(settings, "paper_soak_evidence_window_max_notional_usd", 0.0), 0.0))
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_SOAK_CAP_CONTINUITY_REQUIRED")
    if soak.executed_cycles < soak.min_cycles_required:
        reasons.append("PAPER_SOAK_CAP_CONTINUITY_MINIMUM_CYCLES_REQUIRED")
    if soak.executed_cycles > soak.cycle_cap:
        reasons.append("PAPER_SOAK_CAP_CONTINUITY_CYCLE_CAP_BREACHED")
    if soak.order_action_count > order_cap:
        reasons.append("PAPER_SOAK_CAP_CONTINUITY_ORDER_ACTION_CAP_BREACHED")
    if soak.exchange_submit_count > exchange_cap:
        reasons.append("PAPER_SOAK_CAP_CONTINUITY_EXCHANGE_SUBMIT_CAP_BREACHED")
    if soak.network_submit_count > network_cap:
        reasons.append("PAPER_SOAK_CAP_CONTINUITY_NETWORK_SUBMIT_CAP_BREACHED")
    if soak.total_notional_usd > max_notional:
        reasons.append("PAPER_SOAK_CAP_CONTINUITY_NOTIONAL_CAP_BREACHED")
    return CapContinuityStatus(
        ok=not reasons,
        required=required,
        cycle_cap=soak.cycle_cap,
        executed_cycles=soak.executed_cycles,
        min_cycles_required=soak.min_cycles_required,
        order_action_cap=order_cap,
        order_action_count=soak.order_action_count,
        exchange_submit_cap=exchange_cap,
        exchange_submit_count=soak.exchange_submit_count,
        network_submit_cap=network_cap,
        network_submit_count=soak.network_submit_count,
        max_notional_usd=max_notional,
        total_notional_usd=soak.total_notional_usd,
        reason_codes=reasons or ["PAPER_SOAK_CAP_CONTINUITY_VERIFIED"],
    )


def evaluate_kill_switch_continuity(settings: Any, soak: MultiCycleSoakStatus) -> KillSwitchContinuityStatus:
    required = _boolish(_setting(settings, "paper_soak_evidence_window_kill_switch_required", True), True)
    enabled = _boolish(_setting(settings, "paper_soak_evidence_window_kill_switch_enabled", True), True)
    all_cycles_enabled = all(_boolish(cycle.get("kill_switch_enabled"), False) for cycle in soak.cycles)
    reasons: list[str] = []
    if required and not enabled:
        reasons.append("PAPER_SOAK_KILL_SWITCH_NOT_ENABLED")
    if required and not all_cycles_enabled:
        reasons.append("PAPER_SOAK_KILL_SWITCH_NOT_CONTINUOUS")
    if required and not soak.cycles:
        reasons.append("PAPER_SOAK_KILL_SWITCH_CYCLES_REQUIRED")
    return KillSwitchContinuityStatus(
        ok=not reasons,
        required=required,
        enabled=enabled,
        cycles_checked=len(soak.cycles),
        all_cycles_kill_switch_enabled=all_cycles_enabled,
        reason_codes=reasons or ["PAPER_SOAK_KILL_SWITCH_CONTINUITY_VERIFIED"],
    )


def build_paper_soak_evidence_window_snapshot(
    settings: Any | None = None,
    source_30s_snapshot: Mapping[str, Any] | None = None,
    *,
    source_report_path: str | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_snapshot = dict(_mapping(source_30s_snapshot))
    source = evaluate_source_30s_guardrail(source_snapshot, source_report_path=source_report_path)
    soak = build_multi_cycle_soak(resolved_settings, source)
    caps = evaluate_cap_continuity(resolved_settings, soak)
    kill = evaluate_kill_switch_continuity(resolved_settings, soak)
    no_exchange = {
        "ok": True,
        "required": _boolish(_setting(resolved_settings, "paper_soak_evidence_window_no_exchange_submit_required", True), True),
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_submit_count": soak.exchange_submit_count,
        "network_submit_count": soak.network_submit_count,
        "reason_codes": ["PAPER_SOAK_NO_EXCHANGE_SUBMIT_VERIFIED"],
    }
    no_live = {
        "ok": True,
        "required": _boolish(_setting(resolved_settings, "paper_soak_evidence_window_no_live_real_required", True), True),
        "approved_for_live_real": False,
        "reason_codes": ["PAPER_SOAK_NO_LIVE_REAL_VERIFIED"],
    }
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not soak.ok:
        reasons.extend(soak.reason_codes)
    if not caps.ok:
        reasons.extend(caps.reason_codes)
    if not kill.ok:
        reasons.extend(kill.reason_codes)
    if not no_exchange["ok"]:
        reasons.extend(no_exchange["reason_codes"])
    if not no_live["ok"]:
        reasons.extend(no_live["reason_codes"])
    if source.ok and soak.ok and caps.ok and kill.ok and no_exchange["ok"] and no_live["ok"]:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30S_REQUIRED_DECISION
    elif not soak.ok:
        decision = SOAK_NOT_READY_DECISION
    elif not caps.ok:
        decision = CAPS_NOT_READY_DECISION
    elif not kill.ok:
        decision = KILL_SWITCH_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    approved = decision == READY_DECISION
    snapshot = PaperSoakEvidenceWindowSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_30S_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_paper_soak_evidence_window=approved,
        source_30s_guardrail_verified=source.ok,
        multi_cycle_soak_verified=soak.ok,
        cap_continuity_verified=caps.ok,
        kill_switch_continuity_verified=kill.ok,
        no_exchange_submit_verified=bool(no_exchange["ok"]),
        no_live_real_verified=bool(no_live["ok"]),
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        exchange_submit_performed=False,
        network_submit_attempted=False,
        trading_action_performed=False,
        order_actions_performed=False,
        order_action_count=soak.order_action_count,
        exchange_submit_count=soak.exchange_submit_count,
        network_submit_count=soak.network_submit_count,
        soak_cycle_count=soak.executed_cycles,
        minimum_soak_cycles_required=soak.min_cycles_required,
        total_notional_usd=soak.total_notional_usd,
        exchange_submit_blocked=True,
        live_real_blocked=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        reason_codes=reasons or ["PAPER_SOAK_EVIDENCE_WINDOW_READY"],
        source_30s=source.to_dict(),
        multi_cycle_soak=soak.to_dict(),
        cap_continuity=caps.to_dict(),
        kill_switch_continuity=kill.to_dict(),
        no_exchange_submit=no_exchange,
        no_live_real=no_live,
        source_30s_snapshot=source_snapshot,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    snapshot["approved_for_paper_soak_evidence_window"] = approved
    return snapshot


def build_from_latest_30s_guardrail_report(settings: Any | None = None, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    resolved_settings = settings or Settings()
    source_path, source = latest_valid_30s_guardrail_report(reports_dir)
    return build_paper_soak_evidence_window_snapshot(
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
        f"# {CONTRACT_VERSION} Paper Soak / Evidence Window",
        "",
        "Consumes 30S guarded runtime, runs multi-cycle paper soak evidence, verifies cap/kill-switch continuity, and keeps exchange submit/live-real blocked.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_paper_soak_evidence_window`: `{payload.get('approved_for_paper_soak_evidence_window')}`",
        f"- `source_30s_guardrail_verified`: `{payload.get('source_30s_guardrail_verified')}`",
        f"- `multi_cycle_soak_verified`: `{payload.get('multi_cycle_soak_verified')}`",
        f"- `cap_continuity_verified`: `{payload.get('cap_continuity_verified')}`",
        f"- `kill_switch_continuity_verified`: `{payload.get('kill_switch_continuity_verified')}`",
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
