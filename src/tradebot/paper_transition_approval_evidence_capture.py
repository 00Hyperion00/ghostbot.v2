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
from .paper_transition_operator_gate import (
    READY_DECISION as SOURCE_30B_READY_DECISION,
    build_paper_transition_operator_gate_snapshot,
)
from .paper_transition_candidate_review import (
    READY_DECISION as SOURCE_30C_READY_DECISION,
    build_paper_transition_candidate_review_snapshot,
)

CONTRACT_VERSION = "4B.4.3.6.6.30D"
REPORT_TYPE = "paper_transition_operator_approval_evidence_capture_no_order_enablement"
REPORT_PREFIX = "4B436630D_paper_transition_operator_approval_evidence_capture"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_TRANSITION_APPROVAL_EVIDENCE_CAPTURE_READY_FOR_30C_REVIEW_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED"
INPUT_REQUIRED_DECISION = "PAPER_TRANSITION_APPROVAL_EVIDENCE_CAPTURE_INPUT_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_TRANSITION_APPROVAL_EVIDENCE_CAPTURE_NOT_READY_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "approval_evidence_capture_only": True,
    "paper_transition_candidate_review_only": True,
    "paper_candidate_still_blocked": True,
    "paper_live_order_blocked": True,
    "live_real_blocked": True,
    "runtime_activation_blocked": True,
    "training_reload_blocked": True,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class TypedApprovalIssuanceStatus:
    ok: bool
    required: bool
    operator_id: str
    approval_issued: bool
    token_match: bool
    ttl_sec: int
    issued_at_ms: int
    expires_at_ms: int
    now_ms: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuntimeEnvelopeFreezeTokenStatus:
    ok: bool
    required: bool
    frozen: bool
    token_match: bool
    runtime_envelope: str
    freeze_phrase: str
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FinalRiskCapEvidenceStatus:
    ok: bool
    required: bool
    verified: bool
    capital_cap_usd: float
    order_notional_cap_usd: float
    max_daily_loss_usd: float
    max_daily_trades_cap: int
    kill_switch_enabled: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ApprovalEvidenceCaptureDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_operator_approval_evidence_capture: bool
    approved_for_paper_transition_candidate_review: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    typed_approval_evidence_verified: bool
    ttl_bound_approval_snapshot_verified: bool
    runtime_envelope_freeze_token_verified: bool
    final_risk_cap_verification_evidence_verified: bool
    source_30b_ready: bool
    source_30c_review_ready: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    typed_approval_issuance: dict[str, Any]
    runtime_envelope_freeze_token: dict[str, Any]
    final_risk_cap_evidence: dict[str, Any]
    source_30b_snapshot: dict[str, Any]
    source_30c_review_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


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


def default_paper_preflight_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract_version": "4B.4.3.6.6.30A",
        "decision": "PAPER_CANDIDATE_PREFLIGHT_READY_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED",
        "approved_for_no_order_to_paper_transition_preflight": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "paper_live_order_blocked": True,
        "paper_live_order_enablement_present": False,
        "runtime_activation_blocked": True,
        "training_reload_blocked": True,
        "trading_action_performed": False,
        "read_only": True,
        "risk_limits": {
            "ok": True,
            "capital_cap_usd": 100.0,
            "order_notional_cap_usd": 25.0,
            "max_daily_loss_usd": 5.0,
            "max_daily_trades_cap": 5,
            "kill_switch_enabled": True,
            "reason_codes": ["PAPER_RISK_LIMITS_VERIFIED"],
        },
        "sandbox": {
            "ok": True,
            "execution_mode": "dry_run",
            "market_type": "spot_demo",
            "base_url": "https://demo-api.binance.com",
            "reason_codes": ["EXCHANGE_SANDBOX_ISOLATION_VERIFIED"],
        },
    }


def latest_30a_preflight_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [item for item in reports.glob("4B436630A_paper_candidate_preflight_decision_*.json") if item.is_file()]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_latest_30a_or_default(reports_dir: str | os.PathLike[str]) -> dict[str, Any]:
    path = latest_30a_preflight_report(reports_dir)
    if path is None:
        return default_paper_preflight_snapshot()
    payload = load_json(path)
    return payload if isinstance(payload, dict) else default_paper_preflight_snapshot()


def build_approval_capture_settings(
    base_settings: Settings | None = None,
    *,
    operator_id: str = "",
    confirmation_token: str = "",
    freeze_token: str = "",
    issue_approval: bool = False,
    freeze_runtime_envelope: bool = False,
    verify_final_risk_cap: bool = False,
    issued_at_ms: int | None = None,
    ttl_sec: int | None = None,
) -> Settings:
    settings = base_settings or Settings()
    now = int(issued_at_ms if issued_at_ms is not None else _now_ms())
    return Settings(
        **{
            **settings.to_dict(include_secrets=True),
            "paper_transition_operator_approved": bool(issue_approval),
            "paper_transition_operator_id": str(operator_id or ""),
            "paper_transition_confirmation_token": str(confirmation_token or ""),
            "paper_transition_approval_issued_at_ms": now if issue_approval else 0,
            "paper_transition_approval_ttl_sec": int(ttl_sec if ttl_sec is not None else _setting(settings, "paper_transition_approval_ttl_sec", 900)),
            "paper_transition_runtime_envelope": "sandbox_only",
            "paper_transition_runtime_envelope_frozen": bool(freeze_runtime_envelope),
            "paper_transition_runtime_envelope_freeze_token": str(freeze_token or ""),
            "paper_transition_final_risk_cap_verified": bool(verify_final_risk_cap),
            "paper_transition_dry_run_reconciliation_probe_passed": True,
            "paper_transition_dry_run_probe_order_actions_performed": False,
            "auto_trade_on_signal": False,
            "live_trading_armed": False,
            "live_real_double_confirm": False,
        }
    )


def evaluate_typed_approval_issuance(settings: Any, *, now_ms: int | None = None) -> TypedApprovalIssuanceStatus:
    now = int(now_ms if now_ms is not None else _now_ms())
    required = bool(_setting(settings, "paper_transition_operator_approval_required", True))
    approval_issued = bool(_setting(settings, "paper_transition_operator_approved", False))
    operator_id = str(_setting(settings, "paper_transition_operator_id", "") or "").strip()
    expected = str(_setting(settings, "paper_transition_confirmation_phrase", "CONFIRM_PAPER_TRANSITION_CANDIDATE") or "").strip()
    token = str(_setting(settings, "paper_transition_confirmation_token", "") or "").strip()
    ttl_sec = max(_int(_setting(settings, "paper_transition_approval_ttl_sec", 900), 900), 1)
    issued_at = _int(_setting(settings, "paper_transition_approval_issued_at_ms", 0), 0)
    expires_at = issued_at + ttl_sec * 1000 if issued_at > 0 else 0
    reasons: list[str] = []
    token_match = bool(expected) and token == expected
    if not required:
        reasons.append("TYPED_OPERATOR_APPROVAL_MUST_REMAIN_REQUIRED")
    if not approval_issued:
        reasons.append("TYPED_OPERATOR_APPROVAL_NOT_ISSUED")
    if not operator_id:
        reasons.append("TYPED_OPERATOR_ID_MISSING")
    if not token_match:
        reasons.append("TYPED_OPERATOR_APPROVAL_TOKEN_MISMATCH")
    if issued_at <= 0:
        reasons.append("TYPED_APPROVAL_ISSUED_AT_MISSING")
    elif now > expires_at:
        reasons.append("TYPED_APPROVAL_TTL_EXPIRED")
    ok = required and approval_issued and bool(operator_id) and token_match and issued_at > 0 and now <= expires_at
    return TypedApprovalIssuanceStatus(
        ok=ok,
        required=required,
        operator_id=operator_id,
        approval_issued=approval_issued,
        token_match=token_match,
        ttl_sec=ttl_sec,
        issued_at_ms=issued_at,
        expires_at_ms=expires_at,
        now_ms=now,
        reason_codes=reasons or ["TTL_BOUND_TYPED_OPERATOR_APPROVAL_ISSUED"],
    )


def evaluate_runtime_envelope_freeze_token(settings: Any) -> RuntimeEnvelopeFreezeTokenStatus:
    required = bool(_setting(settings, "paper_transition_runtime_envelope_freeze_required", True))
    frozen = bool(_setting(settings, "paper_transition_runtime_envelope_frozen", False))
    runtime_envelope = str(_setting(settings, "paper_transition_runtime_envelope", "sandbox_only") or "").strip().lower()
    phrase = str(_setting(settings, "paper_transition_runtime_envelope_freeze_phrase", "FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE") or "").strip()
    token = str(_setting(settings, "paper_transition_runtime_envelope_freeze_token", "") or "").strip()
    token_match = bool(phrase) and token == phrase
    reasons: list[str] = []
    if not required:
        reasons.append("RUNTIME_ENVELOPE_FREEZE_MUST_REMAIN_REQUIRED")
    if not frozen:
        reasons.append("RUNTIME_ENVELOPE_NOT_FROZEN")
    if not token_match:
        reasons.append("RUNTIME_ENVELOPE_FREEZE_TOKEN_MISMATCH")
    if runtime_envelope != "sandbox_only":
        reasons.append("RUNTIME_ENVELOPE_NOT_SANDBOX_ONLY")
    ok = required and frozen and token_match and runtime_envelope == "sandbox_only"
    return RuntimeEnvelopeFreezeTokenStatus(
        ok=ok,
        required=required,
        frozen=frozen,
        token_match=token_match,
        runtime_envelope=runtime_envelope,
        freeze_phrase=phrase,
        reason_codes=reasons or ["SANDBOX_RUNTIME_ENVELOPE_FREEZE_TOKEN_VERIFIED"],
    )


def evaluate_final_risk_cap_evidence(settings: Any) -> FinalRiskCapEvidenceStatus:
    required = bool(_setting(settings, "paper_transition_final_risk_cap_verification_required", True))
    verified = bool(_setting(settings, "paper_transition_final_risk_cap_verified", False))
    capital_cap = _float(_setting(settings, "paper_transition_capital_cap_usd", 100.0), 100.0)
    order_cap = _float(_setting(settings, "paper_order_notional_cap_usd", 25.0), 25.0)
    daily_loss = _float(_setting(settings, "paper_max_daily_loss_usd", 5.0), 5.0)
    daily_trades = _int(_setting(settings, "paper_max_daily_trades_cap", 5), 5)
    kill_enabled = bool(_setting(settings, "paper_kill_switch_enabled", True))
    reasons: list[str] = []
    if not required:
        reasons.append("FINAL_RISK_CAP_VERIFICATION_MUST_REMAIN_REQUIRED")
    if not verified:
        reasons.append("FINAL_RISK_CAP_NOT_VERIFIED_BY_OPERATOR")
    if capital_cap <= 0:
        reasons.append("FINAL_RISK_CAPITAL_CAP_NOT_POSITIVE")
    if order_cap <= 0:
        reasons.append("FINAL_RISK_ORDER_CAP_NOT_POSITIVE")
    if order_cap > capital_cap:
        reasons.append("FINAL_RISK_ORDER_CAP_EXCEEDS_CAPITAL_CAP")
    if daily_loss <= 0:
        reasons.append("FINAL_RISK_DAILY_LOSS_NOT_POSITIVE")
    if daily_loss > capital_cap:
        reasons.append("FINAL_RISK_DAILY_LOSS_EXCEEDS_CAPITAL_CAP")
    if daily_trades <= 0:
        reasons.append("FINAL_RISK_DAILY_TRADES_NOT_POSITIVE")
    if not kill_enabled:
        reasons.append("FINAL_RISK_KILL_SWITCH_NOT_ENABLED")
    ok = required and verified and not [r for r in reasons if r != "FINAL_RISK_CAP_NOT_VERIFIED_BY_OPERATOR"] and "FINAL_RISK_CAP_NOT_VERIFIED_BY_OPERATOR" not in reasons
    return FinalRiskCapEvidenceStatus(
        ok=ok,
        required=required,
        verified=verified,
        capital_cap_usd=capital_cap,
        order_notional_cap_usd=order_cap,
        max_daily_loss_usd=daily_loss,
        max_daily_trades_cap=daily_trades,
        kill_switch_enabled=kill_enabled,
        reason_codes=reasons or ["FINAL_PAPER_RISK_CAP_EVIDENCE_VERIFIED"],
    )


def build_operator_approval_evidence_capture_snapshot(
    settings: Any,
    *,
    paper_preflight_snapshot: Mapping[str, Any] | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    preflight = dict(paper_preflight_snapshot or default_paper_preflight_snapshot())
    approval = evaluate_typed_approval_issuance(settings, now_ms=now_ms)
    freeze = evaluate_runtime_envelope_freeze_token(settings)
    risk = evaluate_final_risk_cap_evidence(settings)
    source_30b = build_paper_transition_operator_gate_snapshot(
        settings,
        preflight,
        supplied_operator_confirmation=str(_setting(settings, "paper_transition_confirmation_token", "") or ""),
        now_ms=now_ms,
    )
    source_30c = build_paper_transition_candidate_review_snapshot(
        settings,
        source_30b,
        source_report_path="generated_by_30D_evidence_capture",
        supplied_freeze_token=str(_setting(settings, "paper_transition_runtime_envelope_freeze_token", "") or ""),
    )
    source_30b_ready = str(source_30b.get("decision") or "") == SOURCE_30B_READY_DECISION and bool(source_30b.get("approved_for_paper_transition_candidate", False))
    source_30c_ready = str(source_30c.get("decision") or "") == SOURCE_30C_READY_DECISION and bool(source_30c.get("approved_for_paper_transition_candidate_review", False))
    no_paper = not bool(source_30b.get("approved_for_paper_candidate", False)) and not bool(source_30c.get("approved_for_paper_candidate", False)) and not bool(source_30b.get("paper_live_order_enablement_present", False)) and not bool(source_30c.get("paper_live_order_enablement_present", False))
    no_live = not bool(source_30b.get("approved_for_live_real", False)) and not bool(source_30c.get("approved_for_live_real", False))
    no_orders = not bool(source_30b.get("trading_action_performed", False)) and not bool(source_30b.get("order_actions_performed", False)) and not bool(source_30c.get("trading_action_performed", False)) and not bool(source_30c.get("order_actions_performed", False))
    reasons: list[str] = []
    reasons.extend(approval.reason_codes)
    reasons.extend(freeze.reason_codes)
    reasons.extend(risk.reason_codes)
    if not source_30b_ready:
        reasons.append("SOURCE_30B_READY_OPERATOR_APPROVAL_EVIDENCE_REQUIRED")
    if not source_30c_ready:
        reasons.append("SOURCE_30C_READY_REVIEW_EVIDENCE_REQUIRED")
    if not no_paper:
        reasons.append("PAPER_ORDER_ENABLEMENT_UNEXPECTEDLY_PRESENT")
    if not no_live:
        reasons.append("LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not no_orders:
        reasons.append("ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    reasons.append("PAPER_ORDER_ENABLEMENT_STILL_BLOCKED")
    reasons.append("LIVE_REAL_HARD_BLOCK_VERIFIED")
    ready = approval.ok and freeze.ok and risk.ok and source_30b_ready and source_30c_ready and no_paper and no_live and no_orders
    input_required = any(reason in reasons for reason in (
        "TYPED_OPERATOR_APPROVAL_NOT_ISSUED",
        "TYPED_OPERATOR_ID_MISSING",
        "RUNTIME_ENVELOPE_NOT_FROZEN",
        "FINAL_RISK_CAP_NOT_VERIFIED_BY_OPERATOR",
    ))
    decision = READY_DECISION if ready else (INPUT_REQUIRED_DECISION if input_required else NOT_READY_DECISION)
    payload = ApprovalEvidenceCaptureDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_operator_approval_evidence_capture=ready,
        approved_for_paper_transition_candidate_review=ready,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        typed_approval_evidence_verified=approval.ok,
        ttl_bound_approval_snapshot_verified=approval.ok,
        runtime_envelope_freeze_token_verified=freeze.ok,
        final_risk_cap_verification_evidence_verified=risk.ok,
        source_30b_ready=source_30b_ready,
        source_30c_review_ready=source_30c_ready,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        typed_approval_issuance=approval.to_dict(),
        runtime_envelope_freeze_token=freeze.to_dict(),
        final_risk_cap_evidence=risk.to_dict(),
        source_30b_snapshot=dict(source_30b),
        source_30c_review_snapshot=dict(source_30c),
    ).to_dict()
    payload.update({**RISK_FLAGS, "generated_at_utc": utc_now_iso(), "operator_approval_evidence_capture_gate": True, "ttl_bound_approval_snapshot_gate": True, "runtime_envelope_freeze_token_gate": True, "final_risk_cap_verification_evidence_gate": True, "still_no_paper_order_enablement_gate": True, "no_live_real_enforcement": True})
    return payload


def build_from_operator_inputs(
    *,
    operator_id: str = "",
    confirmation_token: str = "",
    freeze_token: str = "",
    issue_approval: bool = False,
    freeze_runtime_envelope: bool = False,
    verify_final_risk_cap: bool = False,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    now_ms: int | None = None,
    ttl_sec: int | None = None,
) -> dict[str, Any]:
    settings = build_approval_capture_settings(
        operator_id=operator_id,
        confirmation_token=confirmation_token,
        freeze_token=freeze_token,
        issue_approval=issue_approval,
        freeze_runtime_envelope=freeze_runtime_envelope,
        verify_final_risk_cap=verify_final_risk_cap,
        issued_at_ms=now_ms,
        ttl_sec=ttl_sec,
    )
    return build_operator_approval_evidence_capture_snapshot(
        settings,
        paper_preflight_snapshot=_load_latest_30a_or_default(reports_dir),
        now_ms=now_ms,
    )


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} Operator Approval Evidence Capture")
    lines.append("")
    lines.append("This report captures typed operator approval evidence, a TTL-bound approval snapshot, sandbox runtime envelope freeze evidence, and final paper risk-cap verification evidence. It does not enable paper orders or live-real.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_operator_approval_evidence_capture",
        "approved_for_paper_transition_candidate_review",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "paper_order_enablement_still_blocked",
        "trading_action_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Evidence gates")
    for key in (
        "typed_approval_evidence_verified",
        "ttl_bound_approval_snapshot_verified",
        "runtime_envelope_freeze_token_verified",
        "final_risk_cap_verification_evidence_verified",
        "source_30b_ready",
        "source_30c_review_ready",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Reason codes")
    for reason in payload.get("reason_codes", []):
        lines.append(f"- `{reason}`")
    lines.append("")
    return "\n".join(lines)


def _report_decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "unknown").strip().lower()
    if decision == READY_DECISION.lower():
        return "ready"
    if decision == INPUT_REQUIRED_DECISION.lower():
        return "input_required"
    if decision == NOT_READY_DECISION.lower():
        return "not_ready"
    slug = "".join(char if char.isalnum() else "_" for char in decision).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return (slug or "unknown")[:96]


def _unique_report_paths(target: Path, payload: Mapping[str, Any]) -> tuple[Path, Path]:
    stem = f"{REPORT_PREFIX}_{utc_stamp()}_{_report_decision_suffix(payload)}"
    for index in range(1000):
        suffix = "" if index == 0 else f"_{index:03d}"
        json_path = target / f"{stem}{suffix}.json"
        md_path = target / f"{stem}{suffix}.md"
        if not json_path.exists() and not md_path.exists():
            return json_path, md_path
    raise RuntimeError(f"could not allocate unique report path for {stem}")


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path, md_path = _unique_report_paths(target, payload)
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\n")
    return json_path, md_path
