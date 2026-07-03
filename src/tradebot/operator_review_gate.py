from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436634C"
PATCH_VERSION = "4B.4.3.6.6.34C"
PATCH_NAME = "Operator Review Gate"
READY_DECISION = "OPERATOR_REVIEW_GATE_READY_NO_SUBMIT_RECONFIRMED"
NOT_READY_DECISION = "OPERATOR_REVIEW_GATE_NOT_READY"
SOURCE_34B_DECISION = "EVIDENCE_INVENTORY_RECONCILIATION_READY_POST_34A_BASELINE_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.34D"


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


def run_git(repo_root: Path, args: Sequence[str]) -> tuple[bool, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "", str(exc)
    return proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip()


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
class Source34BEvidenceGate:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    source_34a_complete: bool
    recovery_report_deduplication_complete: bool
    advisory_dirty_worktree_normalizer_complete: bool
    post_34a_evidence_baseline_complete: bool
    dirty_worktree_advisory_only: bool
    dirty_worktree_blocker_count: int
    deduplication_action_performed: bool
    duplicate_group_count: int
    duplicate_report_count: int
    recovery_report_scanned_count: int
    ready_report_count: int
    unknown_report_count: int
    current_dirty_worktree_count: int
    normalized_dirty_worktree_count: int
    submit_boundary_relaxed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    baseline_digest: str | None
    deduplication_digest: str | None
    dirty_worktree_digest: str | None


@dataclass(frozen=True)
class EvidenceBaselineReview:
    complete: bool
    source_34b_report: str | None
    review_status: str
    recovery_report_scanned_count: int
    ready_report_count: int
    unknown_report_count: int
    duplicate_group_count: int
    duplicate_report_count: int
    current_dirty_worktree_count: int
    normalized_dirty_worktree_count: int
    dirty_worktree_blocker_count: int
    dirty_worktree_advisory_only: bool
    deduplication_action_performed: bool
    baseline_digest: str | None
    deduplication_digest: str | None
    dirty_worktree_digest: str | None
    findings: list[str]
    digest: str


@dataclass(frozen=True)
class NoSubmitBoundaryReconfirmation:
    complete: bool
    boundary_status: str
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
    destructive_cleanup_performed: bool
    submit_boundary_relaxed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    digest: str


@dataclass(frozen=True)
class TransitionDecisionLedger:
    complete: bool
    transition_status: str
    operator_review_required: bool
    operator_review_present: bool
    operator_decision_token: str | None
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    next_phase: str
    hold_reason: str
    accepted_review_criterion_count: int
    rejected_review_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class OperatorReviewGateReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_34b_complete: bool
    source_34b_report: str | None
    source_34b_decision: str | None
    evidence_baseline_review_complete: bool
    evidence_baseline_review_status: str
    recovery_report_scanned_count: int
    duplicate_group_count: int
    duplicate_report_count: int
    dirty_worktree_advisory_only: bool
    dirty_worktree_blocker_count: int
    no_submit_boundary_reconfirmation_complete: bool
    no_submit_boundary_status: str
    transition_decision_ledger_complete: bool
    transition_status: str
    operator_review_required: bool
    operator_review_present: bool
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
    destructive_cleanup_performed: bool
    submit_boundary_relaxed: bool
    deduplication_action_performed: bool
    report_delete_performed: bool
    file_move_performed: bool
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    baseline_digest: str | None
    evidence_review_digest: str | None
    no_submit_boundary_digest: str | None
    transition_decision_digest: str | None
    report_path: str | None = None
    evidence_baseline_review_path: str | None = None
    no_submit_boundary_reconfirmation_path: str | None = None
    transition_decision_ledger_path: str | None = None


def parse_source_34b_gate(repo_root: Path) -> Source34BEvidenceGate:
    report_path = find_latest_report(repo_root, "4B436634B_evidence_inventory_reconciliation_*_ready.json")
    if report_path is None:
        return Source34BEvidenceGate(False, None, None, None, "missing_34b_ready_report", False, False, False, False, False, 1, False, 0, 0, 0, 0, 0, 0, 0, False, False, False, None, None, None, None, None)

    data, error = read_json(report_path)
    rel = relative_to_repo(repo_root, report_path)
    if data is None:
        return Source34BEvidenceGate(False, rel, None, None, error, False, False, False, False, False, 1, False, 0, 0, 0, 0, 0, 0, 0, False, False, False, None, None, None, None, None)

    status = str(value(data, "status", default=""))
    decision = str(value(data, "decision", default=""))
    source_34a_complete = bool_value(data, "source_34a_complete", "source_34a_gate.complete")
    dedup_complete = bool_value(data, "recovery_report_deduplication_complete", "recovery_report_deduplication.complete")
    dirty_complete = bool_value(data, "advisory_dirty_worktree_normalizer_complete", "advisory_dirty_worktree_normalizer.complete")
    baseline_complete = bool_value(data, "post_34a_evidence_baseline_complete", "post_34a_evidence_baseline.complete")
    dirty_advisory_only = bool_value(data, "dirty_worktree_advisory_only", "advisory_dirty_worktree_normalizer.advisory_only")
    dirty_blocker_count = int_value(data, "dirty_worktree_blocker_count", "advisory_dirty_worktree_normalizer.blocker_count")
    dedup_action = bool_value(data, "deduplication_action_performed", "recovery_report_deduplication.deletion_performed")
    duplicate_group_count = int_value(data, "duplicate_group_count", "recovery_report_deduplication.duplicate_group_count", "post_34a_evidence_baseline.duplicate_group_count")
    duplicate_report_count = int_value(data, "duplicate_report_count", "recovery_report_deduplication.duplicate_report_count", "post_34a_evidence_baseline.duplicate_report_count")
    scanned_count = int_value(data, "recovery_report_scanned_count", "recovery_report_deduplication.scanned_report_count", "post_34a_evidence_baseline.total_recovery_report_count")
    ready_count = int_value(data, "ready_report_count", "post_34a_evidence_baseline.ready_report_count")
    unknown_count = int_value(data, "unknown_report_count", "post_34a_evidence_baseline.unknown_report_count")
    dirty_count = int_value(data, "current_dirty_worktree_count", "advisory_dirty_worktree_normalizer.current_dirty_worktree_count")
    normalized_dirty_count = int_value(data, "normalized_dirty_worktree_count", "advisory_dirty_worktree_normalizer.normalized_dirty_worktree_count")
    submit_boundary_relaxed = bool_value(data, "submit_boundary_relaxed", "post_34a_evidence_baseline.submit_boundary_relaxed")
    next_unlock_allowed = bool_value(data, "next_phase_unlock_allowed", "post_34a_evidence_baseline.next_phase_unlock_allowed")
    next_unlock_performed = bool_value(data, "next_phase_unlock_performed", "post_34a_evidence_baseline.next_phase_unlock_performed")
    manifest_sha256 = str_or_none(data, "manifest_sha256", "source_34a_gate.manifest_sha256")
    immutable_plan_digest = str_or_none(data, "immutable_plan_digest", "source_34a_gate.immutable_plan_digest")
    baseline_digest = str_or_none(data, "baseline_digest", "post_34a_evidence_baseline.digest")
    dedup_digest = str_or_none(data, "deduplication_digest", "recovery_report_deduplication.digest")
    dirty_digest = str_or_none(data, "dirty_worktree_digest", "advisory_dirty_worktree_normalizer.digest")

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
            "destructive_cleanup_performed",
            "next_phase_unlock_allowed",
            "next_phase_unlock_performed",
            "submit_boundary_relaxed",
            "deduplication_action_performed",
        )
    )

    complete = (
        status == "READY"
        and decision == SOURCE_34B_DECISION
        and source_34a_complete
        and dedup_complete
        and dirty_complete
        and baseline_complete
        and dirty_advisory_only
        and dirty_blocker_count == 0
        and not dedup_action
        and not submit_boundary_relaxed
        and not next_unlock_allowed
        and not next_unlock_performed
        and safety_ok
    )
    return Source34BEvidenceGate(
        complete=complete,
        report=rel,
        status=status or None,
        decision=decision or None,
        error=None if complete else "source_34b_gate_not_complete",
        source_34a_complete=source_34a_complete,
        recovery_report_deduplication_complete=dedup_complete,
        advisory_dirty_worktree_normalizer_complete=dirty_complete,
        post_34a_evidence_baseline_complete=baseline_complete,
        dirty_worktree_advisory_only=dirty_advisory_only,
        dirty_worktree_blocker_count=dirty_blocker_count,
        deduplication_action_performed=dedup_action,
        duplicate_group_count=duplicate_group_count,
        duplicate_report_count=duplicate_report_count,
        recovery_report_scanned_count=scanned_count,
        ready_report_count=ready_count,
        unknown_report_count=unknown_count,
        current_dirty_worktree_count=dirty_count,
        normalized_dirty_worktree_count=normalized_dirty_count,
        submit_boundary_relaxed=submit_boundary_relaxed,
        next_phase_unlock_allowed=next_unlock_allowed,
        next_phase_unlock_performed=next_unlock_performed,
        manifest_sha256=manifest_sha256,
        immutable_plan_digest=immutable_plan_digest,
        baseline_digest=baseline_digest,
        deduplication_digest=dedup_digest,
        dirty_worktree_digest=dirty_digest,
    )


def build_evidence_baseline_review(source: Source34BEvidenceGate) -> EvidenceBaselineReview:
    findings: list[str] = []
    if source.duplicate_report_count > 0:
        findings.append("duplicate_reports_classified_advisory_no_deletion")
    if source.unknown_report_count > 0:
        findings.append("unknown_reports_retained_for_manual_review")
    if source.current_dirty_worktree_count > 0:
        findings.append("dirty_worktree_entries_are_current_phase_advisory")
    if not findings:
        findings.append("post_34a_evidence_baseline_clean")

    complete = bool(
        source.complete
        and source.recovery_report_deduplication_complete
        and source.advisory_dirty_worktree_normalizer_complete
        and source.post_34a_evidence_baseline_complete
        and source.dirty_worktree_advisory_only
        and source.dirty_worktree_blocker_count == 0
        and not source.deduplication_action_performed
    )
    payload = {
        "source_34b_report": source.report,
        "complete": complete,
        "duplicate_group_count": source.duplicate_group_count,
        "duplicate_report_count": source.duplicate_report_count,
        "dirty_worktree_blocker_count": source.dirty_worktree_blocker_count,
        "dirty_worktree_advisory_only": source.dirty_worktree_advisory_only,
        "findings": findings,
    }
    return EvidenceBaselineReview(
        complete=complete,
        source_34b_report=source.report,
        review_status="34B_EVIDENCE_BASELINE_REVIEW_READY_ADVISORY_ONLY" if complete else "34B_EVIDENCE_BASELINE_REVIEW_BLOCKED",
        recovery_report_scanned_count=source.recovery_report_scanned_count,
        ready_report_count=source.ready_report_count,
        unknown_report_count=source.unknown_report_count,
        duplicate_group_count=source.duplicate_group_count,
        duplicate_report_count=source.duplicate_report_count,
        current_dirty_worktree_count=source.current_dirty_worktree_count,
        normalized_dirty_worktree_count=source.normalized_dirty_worktree_count,
        dirty_worktree_blocker_count=source.dirty_worktree_blocker_count,
        dirty_worktree_advisory_only=source.dirty_worktree_advisory_only,
        deduplication_action_performed=source.deduplication_action_performed,
        baseline_digest=source.baseline_digest,
        deduplication_digest=source.deduplication_digest,
        dirty_worktree_digest=source.dirty_worktree_digest,
        findings=findings,
        digest=stable_json_digest(payload),
    )


def build_no_submit_boundary_reconfirmation(source: Source34BEvidenceGate) -> NoSubmitBoundaryReconfirmation:
    complete = bool(source.complete and not source.submit_boundary_relaxed and not source.next_phase_unlock_allowed and not source.next_phase_unlock_performed)
    payload = {
        "complete": complete,
        "source_34b_complete": source.complete,
        "submit_boundary_relaxed": False,
        "next_phase_unlock_allowed": False,
        "all_runtime_submit_flags": False,
    }
    return NoSubmitBoundaryReconfirmation(
        complete=complete,
        boundary_status="NO_SUBMIT_BOUNDARY_RECONFIRMED_LOCKED" if complete else "NO_SUBMIT_BOUNDARY_RECONFIRMATION_BLOCKED",
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
        destructive_cleanup_performed=False,
        submit_boundary_relaxed=False,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        digest=stable_json_digest(payload),
    )


def build_transition_decision_ledger(source: Source34BEvidenceGate, evidence: EvidenceBaselineReview, boundary: NoSubmitBoundaryReconfirmation) -> TransitionDecisionLedger:
    criteria = [
        {"name": "source_34b_ready", "accepted": source.complete},
        {"name": "evidence_baseline_review_complete", "accepted": evidence.complete},
        {"name": "dirty_worktree_advisory_only", "accepted": evidence.dirty_worktree_advisory_only and evidence.dirty_worktree_blocker_count == 0},
        {"name": "no_submit_boundary_reconfirmed", "accepted": boundary.complete and not boundary.submit_boundary_relaxed},
        {"name": "deduplication_no_action", "accepted": not evidence.deduplication_action_performed},
        {"name": "operator_review_required_before_34d", "accepted": True},
        {"name": "transition_not_performed", "accepted": True},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    complete = len(rejected) == 0
    payload = {"criteria": criteria, "next_phase": NEXT_PHASE, "transition_allowed": False, "operator_review_present": False}
    return TransitionDecisionLedger(
        complete=complete,
        transition_status="34C_REVIEW_READY_OPERATOR_DECISION_PENDING_NO_SUBMIT" if complete else "34C_REVIEW_BLOCKED",
        operator_review_required=True,
        operator_review_present=False,
        operator_decision_token=None,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        next_phase=NEXT_PHASE,
        hold_reason="OPERATOR_REVIEW_REQUIRED_NO_SUBMIT_BOUNDARY_LOCKED",
        accepted_review_criterion_count=len(criteria) - len(rejected),
        rejected_review_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_report(repo_root: Path, write: bool = False, reports_dir: Path | None = None) -> OperatorReviewGateReport:
    source = parse_source_34b_gate(repo_root)
    evidence = build_evidence_baseline_review(source)
    boundary = build_no_submit_boundary_reconfirmation(source)
    transition = build_transition_decision_ledger(source, evidence, boundary)

    ok = bool(source.complete and evidence.complete and boundary.complete and transition.complete)
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    report = OperatorReviewGateReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="operator_review_gate",
        status=status,
        ok=ok,
        decision=decision,
        source_34b_complete=source.complete,
        source_34b_report=source.report,
        source_34b_decision=source.decision,
        evidence_baseline_review_complete=evidence.complete,
        evidence_baseline_review_status=evidence.review_status,
        recovery_report_scanned_count=evidence.recovery_report_scanned_count,
        duplicate_group_count=evidence.duplicate_group_count,
        duplicate_report_count=evidence.duplicate_report_count,
        dirty_worktree_advisory_only=evidence.dirty_worktree_advisory_only,
        dirty_worktree_blocker_count=evidence.dirty_worktree_blocker_count,
        no_submit_boundary_reconfirmation_complete=boundary.complete,
        no_submit_boundary_status=boundary.boundary_status,
        transition_decision_ledger_complete=transition.complete,
        transition_status=transition.transition_status,
        operator_review_required=transition.operator_review_required,
        operator_review_present=transition.operator_review_present,
        transition_to_next_phase_allowed=transition.transition_to_next_phase_allowed,
        transition_to_next_phase_performed=transition.transition_to_next_phase_performed,
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
        destructive_cleanup_performed=False,
        submit_boundary_relaxed=False,
        deduplication_action_performed=False,
        report_delete_performed=False,
        file_move_performed=False,
        manifest_sha256=source.manifest_sha256,
        immutable_plan_digest=source.immutable_plan_digest,
        baseline_digest=source.baseline_digest,
        evidence_review_digest=evidence.digest,
        no_submit_boundary_digest=boundary.digest,
        transition_decision_digest=transition.digest,
    )

    if not write:
        return report

    out_dir = reports_dir or (repo_root / "reports" / "recovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_timestamp()
    suffix = status.lower()
    evidence_path = out_dir / f"{PATCH_ID}_34b_evidence_baseline_review_{ts}.json"
    boundary_path = out_dir / f"{PATCH_ID}_no_submit_boundary_reconfirmation_{ts}.json"
    transition_path = out_dir / f"{PATCH_ID}_transition_decision_ledger_{ts}.json"
    report_path = out_dir / f"{PATCH_ID}_operator_review_gate_{ts}_{suffix}.json"

    evidence_path.write_text(json.dumps(asdict(evidence), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    boundary_path.write_text(json.dumps(asdict(boundary), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    transition_path.write_text(json.dumps(asdict(transition), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    final_report = OperatorReviewGateReport(
        **{
            **asdict(report),
            "report_path": str(report_path),
            "evidence_baseline_review_path": str(evidence_path),
            "no_submit_boundary_reconfirmation_path": str(boundary_path),
            "transition_decision_ledger_path": str(transition_path),
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
