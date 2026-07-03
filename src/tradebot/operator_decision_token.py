from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436634D"
PATCH_VERSION = "4B.4.3.6.6.34D"
PATCH_NAME = "Operator Decision Token"
READY_DECISION = "OPERATOR_DECISION_TOKEN_READY_FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED"
NOT_READY_DECISION = "OPERATOR_DECISION_TOKEN_NOT_READY"
SOURCE_34C_DECISION = "OPERATOR_REVIEW_GATE_READY_NO_SUBMIT_RECONFIRMED"
NEXT_PHASE = "4B.4.3.6.6.34E"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None, f"missing:{path}"
    except json.JSONDecodeError as exc:
        return None, f"json_decode:{path}:{exc}"
    except OSError as exc:
        return None, f"os_error:{path}:{exc}"
    if not isinstance(data, dict):
        return None, f"non_object_root:{path}"
    return data, None


def value(data: Mapping[str, Any], *paths: str, default: Any = None) -> Any:
    for path in paths:
        current: Any = data
        found = True
        for part in path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                found = False
                break
        if found:
            return current
    return default


def bool_value(data: Mapping[str, Any], *paths: str, default: bool = False) -> bool:
    raw = value(data, *paths, default=None)
    if raw is None:
        return default
    return bool(raw)


def int_value(data: Mapping[str, Any], *paths: str, default: int = 0) -> int:
    raw = value(data, *paths, default=None)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def str_or_none(data: Mapping[str, Any], *paths: str) -> str | None:
    raw = value(data, *paths, default=None)
    return str(raw) if raw is not None else None


def false_or_missing(data: Mapping[str, Any], *paths: str) -> bool:
    for path in paths:
        raw = value(data, path, default=None)
        if raw is not None:
            return raw is False
    return True


def stable_json_digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def find_latest_report(repo_root: Path, pattern: str) -> Path | None:
    reports_dir = repo_root / "reports" / "recovery"
    matches = sorted(reports_dir.glob(pattern))
    return matches[-1] if matches else None


@dataclass(frozen=True)
class Source34COperatorGate:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    source_34b_complete: bool
    evidence_baseline_review_complete: bool
    no_submit_boundary_reconfirmation_complete: bool
    transition_decision_ledger_complete: bool
    operator_review_required: bool
    operator_review_present: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    dirty_worktree_advisory_only: bool
    dirty_worktree_blocker_count: int
    deduplication_action_performed: bool
    report_delete_performed: bool
    file_move_performed: bool
    duplicate_group_count: int
    duplicate_report_count: int
    recovery_report_scanned_count: int
    submit_boundary_relaxed: bool
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    baseline_digest: str | None
    evidence_review_digest: str | None
    no_submit_boundary_digest: str | None
    transition_decision_digest: str | None


@dataclass(frozen=True)
class HumanReviewSignatureLedger:
    complete: bool
    source_34c_report: str | None
    signature_required: bool
    signature_present: bool
    signature_status: str
    operator_decision_token_present: bool
    operator_decision_token_hash: str | None
    accepted_signature_criterion_count: int
    rejected_signature_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class TransitionEligibilityDryRun:
    complete: bool
    eligibility_status: str
    source_34c_complete: bool
    human_review_signature_present: bool
    evidence_baseline_review_complete: bool
    no_submit_boundary_reconfirmation_complete: bool
    transition_decision_ledger_complete: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    next_phase: str
    dry_run_only: bool
    hold_reason: str
    accepted_eligibility_criterion_count: int
    rejected_eligibility_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class FinalNoSubmitUnlockBoundary:
    complete: bool
    boundary_status: str
    unlock_boundary_locked: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    exchange_submit_allowed: bool
    network_submit_allowed: bool
    runtime_overlay_allowed: bool
    order_submit_performed: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    file_move_performed: bool
    report_delete_performed: bool
    destructive_cleanup_performed: bool
    deduplication_action_performed: bool
    submit_boundary_relaxed: bool
    digest: str


@dataclass(frozen=True)
class OperatorDecisionTokenReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_34c_complete: bool
    source_34c_report: str | None
    source_34c_decision: str | None
    human_review_signature_ledger_complete: bool
    human_review_signature_required: bool
    human_review_signature_present: bool
    human_review_signature_status: str
    operator_decision_token_present: bool
    transition_eligibility_dry_run_complete: bool
    transition_eligibility_status: str
    final_no_submit_unlock_boundary_complete: bool
    final_no_submit_unlock_boundary_status: str
    unlock_boundary_locked: bool
    evidence_baseline_review_complete: bool
    no_submit_boundary_reconfirmation_complete: bool
    transition_decision_ledger_complete: bool
    dirty_worktree_advisory_only: bool
    dirty_worktree_blocker_count: int
    deduplication_action_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    next_phase: str
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    exchange_submit_allowed: bool
    network_submit_allowed: bool
    runtime_overlay_allowed: bool
    order_submit_performed: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    file_move_performed: bool
    report_delete_performed: bool
    destructive_cleanup_performed: bool
    submit_boundary_relaxed: bool
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    baseline_digest: str | None
    evidence_review_digest: str | None
    no_submit_boundary_digest: str | None
    transition_decision_digest: str | None
    human_review_signature_digest: str | None
    transition_eligibility_digest: str | None
    final_no_submit_unlock_boundary_digest: str | None
    report_path: str | None = None
    human_review_signature_ledger_path: str | None = None
    transition_eligibility_dry_run_path: str | None = None
    final_no_submit_unlock_boundary_path: str | None = None


def parse_source_34c_gate(repo_root: Path) -> Source34COperatorGate:
    report_path = find_latest_report(repo_root, "4B436634C_operator_review_gate_*_ready.json")
    if report_path is None:
        return Source34COperatorGate(False, None, None, None, "missing_34c_ready_report", False, False, False, False, True, False, False, False, False, False, False, 1, False, False, False, 0, 0, 0, False, None, None, None, None, None, None)

    data, error = read_json(report_path)
    rel = relative_to_repo(repo_root, report_path)
    if data is None:
        return Source34COperatorGate(False, rel, None, None, error, False, False, False, False, True, False, False, False, False, False, False, 1, False, False, False, 0, 0, 0, False, None, None, None, None, None, None)

    status = str(value(data, "status", default=""))
    decision = str(value(data, "decision", default=""))
    source_34b_complete = bool_value(data, "source_34b_complete", "source_34b_gate.complete")
    evidence_complete = bool_value(data, "evidence_baseline_review_complete", "evidence_baseline_review.complete")
    boundary_complete = bool_value(data, "no_submit_boundary_reconfirmation_complete", "no_submit_boundary_reconfirmation.complete")
    transition_complete = bool_value(data, "transition_decision_ledger_complete", "transition_decision_ledger.complete")
    operator_review_required = bool_value(data, "operator_review_required", "transition_decision_ledger.operator_review_required", default=True)
    operator_review_present = bool_value(data, "operator_review_present", "transition_decision_ledger.operator_review_present")
    transition_allowed = bool_value(data, "transition_to_next_phase_allowed", "transition_decision_ledger.transition_to_next_phase_allowed")
    transition_performed = bool_value(data, "transition_to_next_phase_performed", "transition_decision_ledger.transition_to_next_phase_performed")
    next_unlock_allowed = bool_value(data, "next_phase_unlock_allowed", "no_submit_boundary_reconfirmation.next_phase_unlock_allowed")
    next_unlock_performed = bool_value(data, "next_phase_unlock_performed", "no_submit_boundary_reconfirmation.next_phase_unlock_performed")
    dirty_advisory_only = bool_value(data, "dirty_worktree_advisory_only", "evidence_baseline_review.dirty_worktree_advisory_only")
    dirty_blocker_count = int_value(data, "dirty_worktree_blocker_count", "evidence_baseline_review.dirty_worktree_blocker_count")
    dedup_action = bool_value(data, "deduplication_action_performed", "evidence_baseline_review.deduplication_action_performed")
    report_delete = bool_value(data, "report_delete_performed")
    file_move = bool_value(data, "file_move_performed")
    duplicate_group_count = int_value(data, "duplicate_group_count", "evidence_baseline_review.duplicate_group_count")
    duplicate_report_count = int_value(data, "duplicate_report_count", "evidence_baseline_review.duplicate_report_count")
    scanned_count = int_value(data, "recovery_report_scanned_count", "evidence_baseline_review.recovery_report_scanned_count")
    submit_boundary_relaxed = bool_value(data, "submit_boundary_relaxed", "no_submit_boundary_reconfirmation.submit_boundary_relaxed")
    manifest_sha256 = str_or_none(data, "manifest_sha256", "source_34b_gate.manifest_sha256")
    immutable_plan_digest = str_or_none(data, "immutable_plan_digest", "source_34b_gate.immutable_plan_digest")
    baseline_digest = str_or_none(data, "baseline_digest", "evidence_baseline_review.baseline_digest")
    evidence_review_digest = str_or_none(data, "evidence_review_digest", "evidence_baseline_review.digest")
    no_submit_boundary_digest = str_or_none(data, "no_submit_boundary_digest", "no_submit_boundary_reconfirmation.digest")
    transition_decision_digest = str_or_none(data, "transition_decision_digest", "transition_decision_ledger.digest")

    safety_ok = all(
        false_or_missing(data, path)
        for path in (
            "approved_for_live_real",
            "approved_for_paper_transition",
            "approved_for_exchange_submit",
            "approved_for_runtime_overlay",
            "live_real_submit_allowed",
            "paper_submit_allowed",
            "exchange_submit_allowed",
            "network_submit_allowed",
            "runtime_overlay_allowed",
            "exchange_submit_performed",
            "order_submit_performed",
            "trading_action_performed",
            "training_performed",
            "reload_performed",
            "runtime_overlay_activated",
            "archive_execution_allowed",
            "archive_move_performed",
            "file_delete_performed",
            "file_move_performed",
            "report_delete_performed",
            "destructive_cleanup_performed",
            "next_phase_unlock_allowed",
            "next_phase_unlock_performed",
            "transition_to_next_phase_allowed",
            "transition_to_next_phase_performed",
            "submit_boundary_relaxed",
            "deduplication_action_performed",
        )
    )

    complete = bool(
        status == "READY"
        and decision == SOURCE_34C_DECISION
        and source_34b_complete
        and evidence_complete
        and boundary_complete
        and transition_complete
        and operator_review_required
        and not operator_review_present
        and not transition_allowed
        and not transition_performed
        and not next_unlock_allowed
        and not next_unlock_performed
        and dirty_advisory_only
        and dirty_blocker_count == 0
        and not dedup_action
        and not report_delete
        and not file_move
        and not submit_boundary_relaxed
        and safety_ok
    )

    return Source34COperatorGate(
        complete=complete,
        report=rel,
        status=status or None,
        decision=decision or None,
        error=None if complete else "source_34c_gate_not_complete",
        source_34b_complete=source_34b_complete,
        evidence_baseline_review_complete=evidence_complete,
        no_submit_boundary_reconfirmation_complete=boundary_complete,
        transition_decision_ledger_complete=transition_complete,
        operator_review_required=operator_review_required,
        operator_review_present=operator_review_present,
        transition_to_next_phase_allowed=transition_allowed,
        transition_to_next_phase_performed=transition_performed,
        next_phase_unlock_allowed=next_unlock_allowed,
        next_phase_unlock_performed=next_unlock_performed,
        dirty_worktree_advisory_only=dirty_advisory_only,
        dirty_worktree_blocker_count=dirty_blocker_count,
        deduplication_action_performed=dedup_action,
        report_delete_performed=report_delete,
        file_move_performed=file_move,
        duplicate_group_count=duplicate_group_count,
        duplicate_report_count=duplicate_report_count,
        recovery_report_scanned_count=scanned_count,
        submit_boundary_relaxed=submit_boundary_relaxed,
        manifest_sha256=manifest_sha256,
        immutable_plan_digest=immutable_plan_digest,
        baseline_digest=baseline_digest,
        evidence_review_digest=evidence_review_digest,
        no_submit_boundary_digest=no_submit_boundary_digest,
        transition_decision_digest=transition_decision_digest,
    )


def build_human_review_signature_ledger(source: Source34COperatorGate) -> HumanReviewSignatureLedger:
    token: str | None = None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest() if token else None
    criteria = [
        {"name": "source_34c_ready", "accepted": source.complete},
        {"name": "operator_signature_required", "accepted": True},
        {"name": "operator_signature_absent_no_unlock_only", "accepted": token is None},
        {"name": "no_transition_without_signature", "accepted": not source.transition_to_next_phase_allowed and not source.transition_to_next_phase_performed},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    complete = len(rejected) == 0
    payload = {
        "source_34c_report": source.report,
        "signature_required": True,
        "signature_present": False,
        "token_hash": token_hash,
        "criteria": criteria,
    }
    return HumanReviewSignatureLedger(
        complete=complete,
        source_34c_report=source.report,
        signature_required=True,
        signature_present=False,
        signature_status="HUMAN_REVIEW_SIGNATURE_NOT_PRESENT_NO_UNLOCK_ONLY" if complete else "HUMAN_REVIEW_SIGNATURE_LEDGER_BLOCKED",
        operator_decision_token_present=False,
        operator_decision_token_hash=token_hash,
        accepted_signature_criterion_count=len(criteria) - len(rejected),
        rejected_signature_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_transition_eligibility_dry_run(source: Source34COperatorGate, signature: HumanReviewSignatureLedger) -> TransitionEligibilityDryRun:
    criteria = [
        {"name": "source_34c_complete", "accepted": source.complete},
        {"name": "evidence_baseline_review_complete", "accepted": source.evidence_baseline_review_complete},
        {"name": "no_submit_boundary_reconfirmed", "accepted": source.no_submit_boundary_reconfirmation_complete and not source.submit_boundary_relaxed},
        {"name": "transition_decision_ledger_complete", "accepted": source.transition_decision_ledger_complete},
        {"name": "human_signature_absent_hold", "accepted": not signature.signature_present},
        {"name": "transition_allowed_false", "accepted": not source.transition_to_next_phase_allowed},
        {"name": "transition_performed_false", "accepted": not source.transition_to_next_phase_performed},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    complete = len(rejected) == 0
    payload = {
        "criteria": criteria,
        "next_phase": NEXT_PHASE,
        "dry_run_only": True,
        "transition_allowed": False,
    }
    return TransitionEligibilityDryRun(
        complete=complete,
        eligibility_status="TRANSITION_ELIGIBILITY_DRY_RUN_HOLD_OPERATOR_SIGNATURE_REQUIRED" if complete else "TRANSITION_ELIGIBILITY_DRY_RUN_BLOCKED",
        source_34c_complete=source.complete,
        human_review_signature_present=signature.signature_present,
        evidence_baseline_review_complete=source.evidence_baseline_review_complete,
        no_submit_boundary_reconfirmation_complete=source.no_submit_boundary_reconfirmation_complete,
        transition_decision_ledger_complete=source.transition_decision_ledger_complete,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        next_phase=NEXT_PHASE,
        dry_run_only=True,
        hold_reason="HUMAN_REVIEW_SIGNATURE_REQUIRED_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED",
        accepted_eligibility_criterion_count=len(criteria) - len(rejected),
        rejected_eligibility_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_final_no_submit_unlock_boundary(source: Source34COperatorGate, eligibility: TransitionEligibilityDryRun) -> FinalNoSubmitUnlockBoundary:
    complete = bool(source.complete and eligibility.complete)
    payload = {
        "complete": complete,
        "unlock_boundary_locked": True,
        "next_phase_unlock_allowed": False,
        "transition_to_next_phase_allowed": False,
        "all_submit_flags": False,
    }
    return FinalNoSubmitUnlockBoundary(
        complete=complete,
        boundary_status="FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED" if complete else "FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_BLOCKED",
        unlock_boundary_locked=True,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        live_real_submit_allowed=False,
        paper_submit_allowed=False,
        exchange_submit_allowed=False,
        network_submit_allowed=False,
        runtime_overlay_allowed=False,
        order_submit_performed=False,
        exchange_submit_performed=False,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        archive_execution_allowed=False,
        archive_move_performed=False,
        file_delete_performed=False,
        file_move_performed=False,
        report_delete_performed=False,
        destructive_cleanup_performed=False,
        deduplication_action_performed=False,
        submit_boundary_relaxed=False,
        digest=stable_json_digest(payload),
    )


def build_report(repo_root: Path, write: bool = False, reports_dir: Path | None = None) -> OperatorDecisionTokenReport:
    source = parse_source_34c_gate(repo_root)
    signature = build_human_review_signature_ledger(source)
    eligibility = build_transition_eligibility_dry_run(source, signature)
    boundary = build_final_no_submit_unlock_boundary(source, eligibility)

    ok = bool(source.complete and signature.complete and eligibility.complete and boundary.complete)
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    report = OperatorDecisionTokenReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="operator_decision_token",
        status=status,
        ok=ok,
        decision=decision,
        source_34c_complete=source.complete,
        source_34c_report=source.report,
        source_34c_decision=source.decision,
        human_review_signature_ledger_complete=signature.complete,
        human_review_signature_required=signature.signature_required,
        human_review_signature_present=signature.signature_present,
        human_review_signature_status=signature.signature_status,
        operator_decision_token_present=signature.operator_decision_token_present,
        transition_eligibility_dry_run_complete=eligibility.complete,
        transition_eligibility_status=eligibility.eligibility_status,
        final_no_submit_unlock_boundary_complete=boundary.complete,
        final_no_submit_unlock_boundary_status=boundary.boundary_status,
        unlock_boundary_locked=boundary.unlock_boundary_locked,
        evidence_baseline_review_complete=source.evidence_baseline_review_complete,
        no_submit_boundary_reconfirmation_complete=source.no_submit_boundary_reconfirmation_complete,
        transition_decision_ledger_complete=source.transition_decision_ledger_complete,
        dirty_worktree_advisory_only=source.dirty_worktree_advisory_only,
        dirty_worktree_blocker_count=source.dirty_worktree_blocker_count,
        deduplication_action_performed=False,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        next_phase=NEXT_PHASE,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        live_real_submit_allowed=False,
        paper_submit_allowed=False,
        exchange_submit_allowed=False,
        network_submit_allowed=False,
        runtime_overlay_allowed=False,
        order_submit_performed=False,
        exchange_submit_performed=False,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        archive_execution_allowed=False,
        archive_move_performed=False,
        file_delete_performed=False,
        file_move_performed=False,
        report_delete_performed=False,
        destructive_cleanup_performed=False,
        submit_boundary_relaxed=False,
        manifest_sha256=source.manifest_sha256,
        immutable_plan_digest=source.immutable_plan_digest,
        baseline_digest=source.baseline_digest,
        evidence_review_digest=source.evidence_review_digest,
        no_submit_boundary_digest=source.no_submit_boundary_digest,
        transition_decision_digest=source.transition_decision_digest,
        human_review_signature_digest=signature.digest,
        transition_eligibility_digest=eligibility.digest,
        final_no_submit_unlock_boundary_digest=boundary.digest,
    )

    if not write:
        return report

    out_dir = reports_dir or (repo_root / "reports" / "recovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_timestamp()
    suffix = status.lower()
    signature_path = out_dir / f"{PATCH_ID}_human_review_signature_ledger_{ts}.json"
    eligibility_path = out_dir / f"{PATCH_ID}_transition_eligibility_dry_run_{ts}.json"
    boundary_path = out_dir / f"{PATCH_ID}_final_no_submit_unlock_boundary_{ts}.json"
    report_path = out_dir / f"{PATCH_ID}_operator_decision_token_{ts}_{suffix}.json"

    signature_path.write_text(json.dumps(asdict(signature), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    eligibility_path.write_text(json.dumps(asdict(eligibility), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    boundary_path.write_text(json.dumps(asdict(boundary), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    final_report = OperatorDecisionTokenReport(
        **{
            **asdict(report),
            "report_path": str(report_path),
            "human_review_signature_ledger_path": str(signature_path),
            "transition_eligibility_dry_run_path": str(eligibility_path),
            "final_no_submit_unlock_boundary_path": str(boundary_path),
        }
    )
    report_path.write_text(json.dumps(asdict(final_report), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return final_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path.cwd()
    reports_dir = Path(args.reports_dir) if args.reports_dir else None
    report = build_report(repo_root, write=args.write, reports_dir=reports_dir)
    payload = asdict(report)
    if args.once_json:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
