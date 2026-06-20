from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings
from .paper_transition_candidate_review import (
    READY_DECISION as SOURCE_30C_READY_DECISION,
    build_paper_transition_candidate_review_snapshot,
)
from .paper_transition_approval_evidence_capture import (
    READY_DECISION as SOURCE_30D_READY_DECISION,
)

CONTRACT_VERSION = "4B.4.3.6.6.30E"
SOURCE_30D_CONTRACT_VERSION = "4B.4.3.6.6.30D"
SOURCE_30B_CONTRACT_VERSION = "4B.4.3.6.6.30B"
REPORT_TYPE = "paper_transition_review_rerun_consume_30d_ready_evidence"
REPORT_PREFIX = "4B436630E_paper_transition_review_rerun"
DEFAULT_REPORTS_DIR = "reports/production_hardening"

READY_DECISION = "PAPER_TRANSITION_REVIEW_RERUN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED"
EVIDENCE_REQUIRED_DECISION = "PAPER_TRANSITION_REVIEW_RERUN_30D_READY_EVIDENCE_REQUIRED_LIVE_REAL_BLOCKED"
NOT_READY_DECISION = "PAPER_TRANSITION_REVIEW_RERUN_NOT_READY_LIVE_REAL_BLOCKED"

RISK_FLAGS: dict[str, bool] = {
    "read_only": True,
    "paper_transition_review_rerun": True,
    "paper_transition_candidate_review_only": True,
    "paper_candidate_still_blocked": True,
    "paper_live_order_blocked": True,
    "paper_order_enablement_still_blocked": True,
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
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30DReadyEvidenceStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    approved_for_operator_approval_evidence_capture: bool
    approved_for_paper_transition_candidate_review: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    typed_approval_evidence_verified: bool
    ttl_bound_approval_snapshot_verified: bool
    runtime_envelope_freeze_token_verified: bool
    final_risk_cap_verification_evidence_verified: bool
    paper_order_enablement_still_blocked: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Source30CReviewRerunStatus:
    ok: bool
    source_decision: str | None
    approved_for_paper_transition_candidate_review: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    paper_order_enablement_still_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperTransitionReviewRerunDecision:
    contract_version: str
    ok: bool
    decision: str
    approved_for_paper_transition_review_rerun: bool
    approved_for_paper_transition_candidate_review: bool
    approved_for_paper_transition_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    source_30d_ready_evidence_verified: bool
    source_30c_review_rerun_verified: bool
    paper_order_enablement_still_blocked: bool
    live_real_hard_block_verified: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    source_30d_ready_evidence: dict[str, Any]
    source_30c_review_rerun: dict[str, Any]
    source_30d_snapshot: dict[str, Any]
    rerun_30c_snapshot: dict[str, Any]

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


def latest_30d_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    reports = Path(reports_dir)
    matches = [
        item for item in reports.glob("4B436630D_paper_transition_operator_approval_evidence_capture_*_ready.json")
        if item.is_file()
    ]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def evaluate_30d_ready_evidence(source_30d_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30DReadyEvidenceStatus:
    contract = str(source_30d_snapshot.get("contract_version") or "") or None
    decision = str(source_30d_snapshot.get("decision") or "") or None
    evidence_ok = bool(source_30d_snapshot.get("approved_for_operator_approval_evidence_capture", False))
    review_ok = bool(source_30d_snapshot.get("approved_for_paper_transition_candidate_review", False))
    transition_candidate = bool(source_30d_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(source_30d_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(source_30d_snapshot.get("approved_for_live_real", False))
    typed_ok = bool(source_30d_snapshot.get("typed_approval_evidence_verified", False))
    ttl_ok = bool(source_30d_snapshot.get("ttl_bound_approval_snapshot_verified", False))
    freeze_ok = bool(source_30d_snapshot.get("runtime_envelope_freeze_token_verified", False))
    risk_ok = bool(source_30d_snapshot.get("final_risk_cap_verification_evidence_verified", False))
    no_order_enablement = bool(source_30d_snapshot.get("paper_order_enablement_still_blocked", False))
    reasons: list[str] = []
    if contract != SOURCE_30D_CONTRACT_VERSION:
        reasons.append("SOURCE_30D_CONTRACT_VERSION_MISMATCH")
    if decision != SOURCE_30D_READY_DECISION:
        reasons.append("SOURCE_30D_READY_DECISION_REQUIRED")
    if not evidence_ok:
        reasons.append("SOURCE_30D_OPERATOR_EVIDENCE_CAPTURE_NOT_APPROVED")
    if not review_ok:
        reasons.append("SOURCE_30D_REVIEW_EVIDENCE_NOT_MARKED")
    if transition_candidate:
        reasons.append("SOURCE_30D_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("SOURCE_30D_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("SOURCE_30D_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not typed_ok:
        reasons.append("SOURCE_30D_TYPED_APPROVAL_EVIDENCE_NOT_VERIFIED")
    if not ttl_ok:
        reasons.append("SOURCE_30D_TTL_APPROVAL_SNAPSHOT_NOT_VERIFIED")
    if not freeze_ok:
        reasons.append("SOURCE_30D_RUNTIME_FREEZE_TOKEN_NOT_VERIFIED")
    if not risk_ok:
        reasons.append("SOURCE_30D_FINAL_RISK_CAP_EVIDENCE_NOT_VERIFIED")
    if not no_order_enablement:
        reasons.append("SOURCE_30D_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    if bool(source_30d_snapshot.get("trading_action_performed", False)) or bool(source_30d_snapshot.get("order_actions_performed", False)):
        reasons.append("SOURCE_30D_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    ok = not reasons
    return Source30DReadyEvidenceStatus(
        ok=ok,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        approved_for_operator_approval_evidence_capture=evidence_ok,
        approved_for_paper_transition_candidate_review=review_ok,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        typed_approval_evidence_verified=typed_ok,
        ttl_bound_approval_snapshot_verified=ttl_ok,
        runtime_envelope_freeze_token_verified=freeze_ok,
        final_risk_cap_verification_evidence_verified=risk_ok,
        paper_order_enablement_still_blocked=no_order_enablement,
        reason_codes=reasons or ["SOURCE_30D_READY_EVIDENCE_VERIFIED"],
    )


def build_review_rerun_settings(base_settings: Settings | None = None) -> Settings:
    settings = base_settings or Settings()
    payload = settings.to_dict(include_secrets=True)
    payload.update({
        "paper_transition_runtime_envelope": "sandbox_only",
        "paper_transition_runtime_envelope_frozen": True,
        "paper_transition_runtime_envelope_freeze_token": "FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        "paper_transition_final_risk_cap_verified": True,
        "paper_transition_still_no_order_enablement_required": True,
        "auto_trade_on_signal": False,
        "live_trading_armed": False,
        "live_real_double_confirm": False,
    })
    return Settings(**payload)


def rerun_30c_review_from_30d_ready(source_30d_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> dict[str, Any]:
    source_30b = _mapping(source_30d_snapshot.get("source_30b_snapshot"))
    settings = build_review_rerun_settings()
    return build_paper_transition_candidate_review_snapshot(
        settings,
        source_30b,
        source_report_path=source_report_path,
        supplied_freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
    )


def evaluate_30c_review_rerun(rerun_snapshot: Mapping[str, Any]) -> Source30CReviewRerunStatus:
    decision = str(rerun_snapshot.get("decision") or "") or None
    review_ready = bool(rerun_snapshot.get("approved_for_paper_transition_candidate_review", False))
    transition_candidate = bool(rerun_snapshot.get("approved_for_paper_transition_candidate", False))
    paper_candidate = bool(rerun_snapshot.get("approved_for_paper_candidate", False))
    live_real = bool(rerun_snapshot.get("approved_for_live_real", False))
    no_order_enablement = bool(rerun_snapshot.get("paper_order_enablement_still_blocked", False))
    trading_action = bool(rerun_snapshot.get("trading_action_performed", False)) or bool(rerun_snapshot.get("order_actions_performed", False))
    reasons: list[str] = []
    if decision != SOURCE_30C_READY_DECISION:
        reasons.append("RERUN_30C_READY_DECISION_REQUIRED")
    if not review_ready:
        reasons.append("RERUN_30C_REVIEW_READY_NOT_MARKED")
    if transition_candidate:
        reasons.append("RERUN_30C_TRANSITION_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if paper_candidate:
        reasons.append("RERUN_30C_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED")
    if live_real:
        reasons.append("RERUN_30C_LIVE_REAL_UNEXPECTEDLY_APPROVED")
    if not no_order_enablement:
        reasons.append("RERUN_30C_PAPER_ORDER_ENABLEMENT_NOT_BLOCKED")
    if trading_action:
        reasons.append("RERUN_30C_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    ok = not reasons
    return Source30CReviewRerunStatus(
        ok=ok,
        source_decision=decision,
        approved_for_paper_transition_candidate_review=review_ready,
        approved_for_paper_transition_candidate=transition_candidate,
        approved_for_paper_candidate=paper_candidate,
        approved_for_live_real=live_real,
        paper_order_enablement_still_blocked=no_order_enablement,
        trading_action_performed=trading_action,
        reason_codes=reasons or ["RERUN_30C_REVIEW_READY_VERIFIED_NO_ORDER_ENABLEMENT"],
    )


def build_paper_transition_review_rerun_snapshot(
    source_30d_snapshot: Mapping[str, Any],
    *,
    source_report_path: str | None = None,
) -> dict[str, Any]:
    source_evidence = evaluate_30d_ready_evidence(source_30d_snapshot, source_report_path=source_report_path)
    rerun_30c: dict[str, Any] = {}
    if source_evidence.ok:
        rerun_30c = rerun_30c_review_from_30d_ready(source_30d_snapshot, source_report_path=source_report_path)
    rerun_status = evaluate_30c_review_rerun(rerun_30c) if source_evidence.ok else Source30CReviewRerunStatus(
        ok=False,
        source_decision=None,
        approved_for_paper_transition_candidate_review=False,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        paper_order_enablement_still_blocked=True,
        trading_action_performed=False,
        reason_codes=["RERUN_30C_SKIPPED_UNTIL_30D_READY_EVIDENCE"],
    )
    ready = source_evidence.ok and rerun_status.ok
    if ready:
        decision = READY_DECISION
    elif not source_evidence.ok:
        decision = EVIDENCE_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    reasons = [*source_evidence.reason_codes, *rerun_status.reason_codes, "PAPER_ORDER_ENABLEMENT_STILL_BLOCKED", "LIVE_REAL_HARD_BLOCK_VERIFIED"]
    payload = PaperTransitionReviewRerunDecision(
        contract_version=CONTRACT_VERSION,
        ok=True,
        decision=decision,
        approved_for_paper_transition_review_rerun=ready,
        approved_for_paper_transition_candidate_review=ready,
        approved_for_paper_transition_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        source_30d_ready_evidence_verified=source_evidence.ok,
        source_30c_review_rerun_verified=rerun_status.ok,
        paper_order_enablement_still_blocked=True,
        live_real_hard_block_verified=True,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        source_30d_ready_evidence=source_evidence.to_dict(),
        source_30c_review_rerun=rerun_status.to_dict(),
        source_30d_snapshot=dict(source_30d_snapshot),
        rerun_30c_snapshot=dict(rerun_30c),
    ).to_dict()
    payload.update({
        **RISK_FLAGS,
        "generated_at_utc": utc_now_iso(),
        "source_30d_ready_evidence_gate": True,
        "source_30c_review_rerun_gate": True,
        "still_no_paper_order_enablement_gate": True,
        "no_live_real_enforcement": True,
    })
    return payload


def build_from_latest_30d_ready_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    source_path = latest_30d_ready_report(reports_dir)
    source_snapshot = _mapping(load_json(source_path)) if source_path else {}
    return build_paper_transition_review_rerun_snapshot(
        source_snapshot,
        source_report_path=source_path.as_posix() if source_path else None,
    )


def _decision_suffix(payload: Mapping[str, Any]) -> str:
    decision = str(payload.get("decision") or "").upper()
    if decision == READY_DECISION:
        return "ready"
    if decision == EVIDENCE_REQUIRED_DECISION:
        return "30d_required"
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
    lines.append(f"# {CONTRACT_VERSION} Paper Transition Review Re-run")
    lines.append("")
    lines.append("This report consumes a 30D ready evidence capture, re-runs the 30C review gate, and keeps paper order enablement blocked.")
    lines.append("")
    lines.append("## Decision")
    for key in (
        "decision",
        "read_only",
        "approved_for_paper_transition_review_rerun",
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
        "source_30d_ready_evidence_verified",
        "source_30c_review_rerun_verified",
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
