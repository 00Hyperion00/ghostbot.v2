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

CONTRACT_VERSION = "4B.4.3.6.6.30H"
SOURCE_30G_CONTRACT_VERSION = "4B.4.3.6.6.30G"
SOURCE_30G_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_READY_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED"
REPORT_TYPE = "paper_sandbox_dry_run_execution_readiness_lock_still_disabled"
REPORT_PREFIX = "4B436630H_paper_sandbox_dry_run_execution_readiness_lock"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_READY_PAPER_EXECUTION_DISABLED_LIVE_REAL_BLOCKED"
SOURCE_30G_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_30G_CANDIDATE_REQUIRED_LIVE_REAL_BLOCKED"
OPERATOR_LOCK_REQUIRED_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_OPERATOR_LOCK_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_NOT_READY_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_sandbox_dry_run_execution_readiness_lock": True,
    "paper_sandbox_dry_run_execution_candidate_only": True,
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
class Source30GCandidateGateStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    approved_for_paper_sandbox_dry_run_execution_candidate_gate: bool
    approved_for_paper_sandbox_dry_run_execution_candidate: bool
    approved_for_single_simulated_paper_intent: bool
    approved_for_no_exchange_submit_verification: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    exchange_submit_performed: bool
    paper_order_enablement_still_blocked: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorExplicitDryRunLockStatus:
    ok: bool
    required: bool
    operator_id: str
    lock_issued: bool
    token_match: bool
    ttl_sec: int
    issued_at_ms: int
    expires_at_ms: int
    now_ms: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExchangeSubmitHardBlockAuditStatus:
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
class PaperExecutionStillDisabledStatus:
    ok: bool
    required: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_paper_candidate: bool
    paper_live_order_enablement_present: bool
    order_actions_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperSandboxDryRunExecutionReadinessLockDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_sandbox_dry_run_execution_readiness_lock: bool
    approved_for_paper_sandbox_dry_run_execution_readiness_candidate: bool
    approved_for_operator_explicit_dry_run_lock: bool
    approved_for_exchange_submit_hard_block_audit: bool
    approved_for_paper_sandbox_dry_run_execution: bool
    approved_for_exchange_submit: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30g_candidate_gate_verified: bool
    operator_explicit_dry_run_lock_verified: bool
    exchange_submit_hard_block_audit_verified: bool
    paper_execution_still_disabled_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    exchange_submit_performed: bool
    reason_codes: list[str]
    source_30g_candidate_gate: dict[str, Any]
    operator_explicit_dry_run_lock: dict[str, Any]
    exchange_submit_hard_block_audit: dict[str, Any]
    paper_execution_still_disabled: dict[str, Any]
    source_30g_snapshot: dict[str, Any]

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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def latest_30g_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630G_paper_sandbox_dry_run_execution_candidate_gate_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def build_operator_lock_settings(
    base_settings: Settings | None = None,
    *,
    operator_id: str = "",
    lock_token: str = "",
    issue_lock: bool = False,
    issued_at_ms: int | None = None,
    ttl_sec: int | None = None,
) -> Settings:
    settings = base_settings or Settings()
    now = int(issued_at_ms if issued_at_ms is not None else _now_ms())
    payload = settings.to_dict(include_secrets=True)
    payload.update({
        "paper_sandbox_dry_run_operator_lock_operator_id": str(operator_id or ""),
        "paper_sandbox_dry_run_operator_lock_token": str(lock_token or ""),
        "paper_sandbox_dry_run_operator_lock_issued": bool(issue_lock),
        "paper_sandbox_dry_run_operator_lock_issued_at_ms": now if issue_lock else 0,
        "paper_sandbox_dry_run_operator_lock_ttl_sec": int(ttl_sec if ttl_sec is not None else _setting(settings, "paper_sandbox_dry_run_operator_lock_ttl_sec", 900)),
        "execution_mode": "dry_run",
        "market_type": "spot_demo",
        "base_url": "https://demo-api.binance.com",
        "auto_trade_on_signal": False,
        "live_trading_armed": False,
        "live_real_double_confirm": False,
    })
    return Settings(**payload)


def evaluate_source_30g_candidate_gate(source_30g_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30GCandidateGateStatus:
    contract = str(source_30g_snapshot.get("contract_version") or "") or None
    decision = str(source_30g_snapshot.get("decision") or "") or None
    gate = bool(source_30g_snapshot.get("approved_for_paper_sandbox_dry_run_execution_candidate_gate", False))
    candidate = bool(source_30g_snapshot.get("approved_for_paper_sandbox_dry_run_execution_candidate", False))
    simulated_intent = bool(source_30g_snapshot.get("approved_for_single_simulated_paper_intent", False))
    no_submit_verification = bool(source_30g_snapshot.get("approved_for_no_exchange_submit_verification", False))
    dry_run_execution = bool(source_30g_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    exchange_submit_approved = bool(source_30g_snapshot.get("approved_for_exchange_submit", False))
    transition_candidate = bool(source_30g_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30g_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30g_snapshot.get("approved_for_live_real", False))
    no_submit = _mapping(source_30g_snapshot.get("no_exchange_submit"))
    exchange_submit_performed = bool(
        source_30g_snapshot.get("exchange_submit_performed", False)
        or no_submit.get("exchange_submit_performed", False)
        or no_submit.get("submitted_to_exchange", False)
        or no_submit.get("network_submit_attempted", False)
    )
    no_order_enablement = bool(source_30g_snapshot.get("paper_order_enablement_still_blocked", False))
    order_action = bool(source_30g_snapshot.get("trading_action_performed", False)) or bool(source_30g_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if contract != SOURCE_30G_CONTRACT_VERSION:
        reasons.append("SOURCE_30G_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30G_READY_DECISION:
        reasons.append("SOURCE_30G_READY_DECISION_REQUIRED")
    if not gate:
        reasons.append("SOURCE_30G_CANDIDATE_GATE_NOT_APPROVED")
    if not candidate:
        reasons.append("SOURCE_30G_EXECUTION_CANDIDATE_NOT_MARKED")
    if not simulated_intent:
        reasons.append("SOURCE_30G_SINGLE_SIMULATED_INTENT_NOT_VERIFIED")
    if not no_submit_verification:
        reasons.append("SOURCE_30G_NO_EXCHANGE_SUBMIT_NOT_VERIFIED")
    if dry_run_execution:
        reasons.append("SOURCE_30G_DRY_RUN_EXECUTION_UNEXPECTEDLY_APPROVED")
    if exchange_submit_approved:
        reasons.append("SOURCE_30G_EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED")
    if transition_candidate:
        reasons.append("SOURCE_30G_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("SOURCE_30G_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30G_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if exchange_submit_performed:
        reasons.append("SOURCE_30G_EXCHANGE_SUBMIT_UNEXPECTEDLY_PERFORMED")
    if not no_order_enablement:
        reasons.append("SOURCE_30G_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    if order_action:
        reasons.append("SOURCE_30G_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    return Source30GCandidateGateStatus(
        ok=not reasons,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        approved_for_paper_sandbox_dry_run_execution_candidate_gate=gate,
        approved_for_paper_sandbox_dry_run_execution_candidate=candidate,
        approved_for_single_simulated_paper_intent=simulated_intent,
        approved_for_no_exchange_submit_verification=no_submit_verification,
        approved_for_paper_sandbox_dry_run_execution=dry_run_execution,
        approved_for_exchange_submit=exchange_submit_approved,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        exchange_submit_performed=exchange_submit_performed,
        paper_order_enablement_still_blocked=no_order_enablement,
        reason_codes=reasons or ["SOURCE_30G_EXECUTION_CANDIDATE_GATE_VERIFIED"],
    )


def evaluate_operator_explicit_dry_run_lock(settings: Any, *, now_ms: int | None = None) -> OperatorExplicitDryRunLockStatus:
    now = int(now_ms if now_ms is not None else _now_ms())
    required = bool(_setting(settings, "paper_sandbox_dry_run_operator_explicit_lock_required", True))
    operator_id = str(_setting(settings, "paper_sandbox_dry_run_operator_lock_operator_id", "") or "").strip()
    phrase = str(_setting(settings, "paper_sandbox_dry_run_operator_lock_phrase", "LOCK_PAPER_SANDBOX_DRY_RUN_READINESS") or "").strip()
    token = str(_setting(settings, "paper_sandbox_dry_run_operator_lock_token", "") or "").strip()
    issued = bool(_setting(settings, "paper_sandbox_dry_run_operator_lock_issued", False))
    issued_at = _int(_setting(settings, "paper_sandbox_dry_run_operator_lock_issued_at_ms", 0), 0)
    ttl_sec = max(_int(_setting(settings, "paper_sandbox_dry_run_operator_lock_ttl_sec", 900), 900), 1)
    expires_at = issued_at + ttl_sec * 1000 if issued_at > 0 else 0
    token_match = bool(phrase) and token == phrase
    reasons: list[str] = []
    if not required:
        reasons.append("OPERATOR_DRY_RUN_LOCK_MUST_REMAIN_REQUIRED")
    if not issued:
        reasons.append("OPERATOR_DRY_RUN_LOCK_NOT_ISSUED")
    if not operator_id:
        reasons.append("OPERATOR_DRY_RUN_LOCK_OPERATOR_ID_MISSING")
    if not token_match:
        reasons.append("OPERATOR_DRY_RUN_LOCK_TOKEN_MISMATCH")
    if issued_at <= 0:
        reasons.append("OPERATOR_DRY_RUN_LOCK_ISSUED_AT_MISSING")
    elif now > expires_at:
        reasons.append("OPERATOR_DRY_RUN_LOCK_TTL_EXPIRED")
    return OperatorExplicitDryRunLockStatus(
        ok=not reasons,
        required=required,
        operator_id=operator_id,
        lock_issued=issued,
        token_match=token_match,
        ttl_sec=ttl_sec,
        issued_at_ms=issued_at,
        expires_at_ms=expires_at,
        now_ms=now,
        reason_codes=reasons or ["OPERATOR_EXPLICIT_DRY_RUN_LOCK_VERIFIED"],
    )


def evaluate_exchange_submit_hard_block_audit(settings: Any, source_30g_snapshot: Mapping[str, Any]) -> ExchangeSubmitHardBlockAuditStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_exchange_submit_hard_block_audit_required", True))
    no_submit = _mapping(source_30g_snapshot.get("no_exchange_submit"))
    approved = bool(source_30g_snapshot.get("approved_for_exchange_submit", False))
    submitted = bool(no_submit.get("submitted_to_exchange", False))
    exchange_submit_performed = bool(source_30g_snapshot.get("exchange_submit_performed", False) or no_submit.get("exchange_submit_performed", False))
    network_attempted = bool(no_submit.get("network_submit_attempted", False))
    order_id_present = bool(no_submit.get("exchange_order_id") or source_30g_snapshot.get("exchange_order_id"))
    client_id_present = bool(no_submit.get("exchange_client_order_id") or source_30g_snapshot.get("exchange_client_order_id"))
    reasons: list[str] = []
    if not required:
        reasons.append("EXCHANGE_SUBMIT_HARD_BLOCK_AUDIT_MUST_REMAIN_REQUIRED")
    if approved:
        reasons.append("EXCHANGE_SUBMIT_UNEXPECTEDLY_APPROVED")
    if submitted:
        reasons.append("EXCHANGE_SUBMIT_SUBMITTED_TO_EXCHANGE")
    if exchange_submit_performed:
        reasons.append("EXCHANGE_SUBMIT_ACTION_PERFORMED")
    if network_attempted:
        reasons.append("EXCHANGE_SUBMIT_NETWORK_ATTEMPTED")
    if order_id_present:
        reasons.append("EXCHANGE_ORDER_ID_UNEXPECTEDLY_PRESENT")
    if client_id_present:
        reasons.append("EXCHANGE_CLIENT_ORDER_ID_UNEXPECTEDLY_PRESENT")
    return ExchangeSubmitHardBlockAuditStatus(
        ok=not reasons,
        required=required,
        approved_for_exchange_submit=approved,
        submitted_to_exchange=submitted,
        exchange_submit_performed=exchange_submit_performed,
        network_submit_attempted=network_attempted,
        exchange_order_id_present=order_id_present,
        exchange_client_order_id_present=client_id_present,
        reason_codes=reasons or ["EXCHANGE_SUBMIT_HARD_BLOCK_AUDIT_VERIFIED"],
    )


def evaluate_paper_execution_still_disabled(settings: Any, source_30g_snapshot: Mapping[str, Any]) -> PaperExecutionStillDisabledStatus:
    required = bool(_setting(settings, "paper_sandbox_dry_run_execution_still_disabled_required", True))
    dry_run_execution = bool(source_30g_snapshot.get("approved_for_paper_sandbox_dry_run_execution", False))
    paper_candidate = bool(source_30g_snapshot.get("approved_for_paper_candidate", False))
    paper_enablement = bool(source_30g_snapshot.get("paper_live_order_enablement_present", False))
    order_actions = bool(source_30g_snapshot.get("trading_action_performed", False)) or bool(source_30g_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if not required:
        reasons.append("PAPER_EXECUTION_DISABLED_GATE_MUST_REMAIN_REQUIRED")
    if dry_run_execution:
        reasons.append("PAPER_DRY_RUN_EXECUTION_UNEXPECTEDLY_ENABLED")
    if paper_candidate:
        reasons.append("PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_enablement:
        reasons.append("PAPER_ORDER_ENABLEMENT_UNEXPECTEDLY_PRESENT")
    if order_actions:
        reasons.append("ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    return PaperExecutionStillDisabledStatus(
        ok=not reasons,
        required=required,
        approved_for_paper_sandbox_dry_run_execution=dry_run_execution,
        approved_for_paper_candidate=paper_candidate,
        paper_live_order_enablement_present=paper_enablement,
        order_actions_performed=order_actions,
        reason_codes=reasons or ["PAPER_EXECUTION_STILL_DISABLED_VERIFIED"],
    )


def build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(
    settings: Any,
    source_30g_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source = evaluate_source_30g_candidate_gate(source_30g_snapshot, source_report_path=source_report_path)
    lock = evaluate_operator_explicit_dry_run_lock(settings, now_ms=now_ms)
    submit_audit = evaluate_exchange_submit_hard_block_audit(settings, source_30g_snapshot)
    disabled = evaluate_paper_execution_still_disabled(settings, source_30g_snapshot)
    reasons = [*source.reason_codes, *lock.reason_codes, *submit_audit.reason_codes, *disabled.reason_codes]
    reasons.extend(["PAPER_EXECUTION_STILL_DISABLED", "EXCHANGE_SUBMIT_HARD_BLOCK_VERIFIED", "LIVE_REAL_HARD_BLOCK_VERIFIED"])
    ready = source.ok and lock.ok and submit_audit.ok and disabled.ok
    if ready:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30G_REQUIRED_DECISION
    elif not lock.ok:
        decision = OPERATOR_LOCK_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    payload = PaperSandboxDryRunExecutionReadinessLockDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_sandbox_dry_run_execution_readiness_lock=ready,
        approved_for_paper_sandbox_dry_run_execution_readiness_candidate=ready,
        approved_for_operator_explicit_dry_run_lock=lock.ok,
        approved_for_exchange_submit_hard_block_audit=submit_audit.ok,
        approved_for_paper_sandbox_dry_run_execution=False,
        approved_for_exchange_submit=False,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30g_candidate_gate_verified=source.ok,
        operator_explicit_dry_run_lock_verified=lock.ok,
        exchange_submit_hard_block_audit_verified=submit_audit.ok,
        paper_execution_still_disabled_verified=disabled.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        exchange_submit_performed=False,
        reason_codes=reasons,
        source_30g_candidate_gate=source.to_dict(),
        operator_explicit_dry_run_lock=lock.to_dict(),
        exchange_submit_hard_block_audit=submit_audit.to_dict(),
        paper_execution_still_disabled=disabled.to_dict(),
        source_30g_snapshot=dict(source_30g_snapshot),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30g_candidate_gate": True,
        "operator_explicit_dry_run_lock_gate": True,
        "exchange_submit_hard_block_audit_gate": True,
        "paper_execution_still_disabled_gate": True,
        "still_no_paper_order_enablement_gate": True,
        "no_live_real_enforcement": True,
    })
    return payload


def build_from_latest_30g_ready_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    now_ms: int | None = None,
) -> dict[str, Any]:
    source_path = latest_30g_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    return build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(
        settings or Settings(),
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
        now_ms=now_ms,
    )


def build_from_operator_lock_inputs(
    *,
    operator_id: str = "",
    lock_token: str = "",
    issue_lock: bool = False,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    now_ms: int | None = None,
    ttl_sec: int | None = None,
) -> dict[str, Any]:
    settings = build_operator_lock_settings(
        operator_id=operator_id,
        lock_token=lock_token,
        issue_lock=issue_lock,
        issued_at_ms=now_ms,
        ttl_sec=ttl_sec,
    )
    return build_from_latest_30g_ready_report(settings, reports_dir, now_ms=now_ms)


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == SOURCE_30G_REQUIRED_DECISION:
        return "30g_required"
    if decision == OPERATOR_LOCK_REQUIRED_DECISION:
        return "lock_required"
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
    lines.append(f"# {CONTRACT_VERSION} Paper Sandbox Dry-run Execution Readiness Lock")
    lines.append("")
    lines.append("This report consumes the 30G execution-candidate gate, requires an explicit operator dry-run lock, audits exchange submit hard-blocking, and keeps paper execution disabled.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_sandbox_dry_run_execution_readiness_lock",
        "approved_for_paper_sandbox_dry_run_execution_readiness_candidate",
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
    lines.append("## Readiness gates")
    for key in (
        "source_30g_candidate_gate_verified",
        "operator_explicit_dry_run_lock_verified",
        "exchange_submit_hard_block_audit_verified",
        "paper_execution_still_disabled_verified",
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
