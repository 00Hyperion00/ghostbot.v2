from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436634A"
PATCH_VERSION = "4B.4.3.6.6.34A"
PATCH_NAME = "Post-Recovery Next Phase Planning"
READY_DECISION = "POST_RECOVERY_NEXT_PHASE_PLANNING_READY_NO_SUBMIT_BOUNDARY_LOCKED"
NOT_READY_DECISION = "POST_RECOVERY_NEXT_PHASE_PLANNING_NOT_READY"
SOURCE_33I_DECISION = "RECOVERY_CLOSURE_REPORT_READY_NEXT_PHASE_LOCKED_NO_RUNTIME_ACTIONS"
NEXT_PHASE = "4B.4.3.6.6.34B"
REQUIRED_33_TAGS = tuple(f"4B.4.3.6.6.33{suffix}" for suffix in "ABCDEFGHI")


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


def bool_value(data: Mapping[str, Any], *paths: str, default: bool = False) -> bool:
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
            return bool(current)
    return default


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


def int_value(data: Mapping[str, Any], *paths: str, default: int = 0) -> int:
    raw = value(data, *paths, default=default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def false_or_missing(data: Mapping[str, Any], *paths: str) -> bool:
    for path in paths:
        raw = value(data, path, default=None)
        if raw is not None:
            return raw is False
    return True


def count_value(data: Mapping[str, Any], *paths: str, default: int = 0) -> int:
    for path in paths:
        raw = value(data, path, default=None)
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            return len(raw)
        if isinstance(raw, Mapping):
            return len(raw)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    return default


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


def find_latest_report(repo_root: Path, pattern: str) -> Path | None:
    reports_dir = repo_root / "reports" / "recovery"
    matches = sorted(reports_dir.glob(pattern))
    return matches[-1] if matches else None


@dataclass(frozen=True)
class Source33IClosureGate:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    accepted_for_closure: bool
    source_33h_complete: bool
    missing_required_phase_count: int
    rejected_required_phase_count: int
    historical_blocking_condition_count: int
    historical_missing_git_tag_count: int
    historical_dirty_worktree_count: int
    manifest_sha256: str | None
    immutable_plan_digest: str | None


@dataclass(frozen=True)
class GitTagAudit:
    complete: bool
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    current_dirty_worktree_count: int
    required_tag_count: int
    present_tag_count: int
    missing_tag_count: int
    missing_tags: list[str]
    advisory_only: bool
    error: str | None


@dataclass(frozen=True)
class ReadinessScopeDefinition:
    complete: bool
    phase: str
    scope_status: str
    allowed_scope: list[str]
    explicitly_excluded_scope: list[str]
    readiness_inputs: list[str]
    readiness_outputs: list[str]
    risk_manager_note: str
    digest: str


@dataclass(frozen=True)
class NoSubmitTransitionBoundary:
    complete: bool
    boundary_status: str
    submit_boundary_relaxed: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    exchange_submit_allowed: bool
    network_submit_allowed: bool
    runtime_overlay_allowed: bool
    exchange_submit_performed: bool
    order_submit_performed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    destructive_cleanup_performed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    digest: str


@dataclass(frozen=True)
class AcceptanceCriterion:
    criterion_id: str
    description: str
    required: bool
    satisfied: bool
    evidence: str


@dataclass(frozen=True)
class AcceptanceCriteriaMatrix:
    complete: bool
    phase: str
    accepted_criterion_count: int
    required_criterion_count: int
    rejected_required_criterion_count: int
    criteria: list[AcceptanceCriterion]
    digest: str


@dataclass(frozen=True)
class PostRecoveryNextPhasePlanningReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_33i_complete: bool
    source_33i_report: str | None
    source_33i_decision: str | None
    accepted_for_closure: bool
    readiness_scope_definition_complete: bool
    no_submit_transition_boundary_complete: bool
    acceptance_criteria_matrix_complete: bool
    accepted_criterion_count: int
    required_criterion_count: int
    rejected_required_criterion_count: int
    git_tag_audit_complete: bool
    current_dirty_worktree_count: int
    missing_git_tag_count: int
    present_git_tag_count: int
    next_phase: str
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    next_phase_unlock_status: str
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    exchange_submit_allowed: bool
    network_submit_allowed: bool
    runtime_overlay_allowed: bool
    exchange_submit_performed: bool
    order_submit_performed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    destructive_cleanup_performed: bool
    submit_boundary_relaxed: bool
    readiness_scope_digest: str | None
    no_submit_boundary_digest: str | None
    acceptance_matrix_digest: str | None
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    report_path: str | None = None
    readiness_scope_definition_path: str | None = None
    no_submit_transition_boundary_path: str | None = None
    acceptance_criteria_matrix_path: str | None = None


def evaluate_source_33i(repo_root: Path) -> Source33IClosureGate:
    report_path = find_latest_report(repo_root, "4B436633I_recovery_closure_report_*_ready.json")
    if report_path is None:
        return Source33IClosureGate(
            complete=False,
            report=None,
            status=None,
            decision=None,
            error="source_33i_ready_report_missing",
            accepted_for_closure=False,
            source_33h_complete=False,
            missing_required_phase_count=0,
            rejected_required_phase_count=0,
            historical_blocking_condition_count=0,
            historical_missing_git_tag_count=0,
            historical_dirty_worktree_count=0,
            manifest_sha256=None,
            immutable_plan_digest=None,
        )
    data, error = read_json(report_path)
    if data is None:
        return Source33IClosureGate(
            complete=False,
            report=str(report_path.relative_to(repo_root)),
            status=None,
            decision=None,
            error=error,
            accepted_for_closure=False,
            source_33h_complete=False,
            missing_required_phase_count=0,
            rejected_required_phase_count=0,
            historical_blocking_condition_count=0,
            historical_missing_git_tag_count=0,
            historical_dirty_worktree_count=0,
            manifest_sha256=None,
            immutable_plan_digest=None,
        )

    status = str(value(data, "status", default=""))
    decision = str(value(data, "decision", default=""))
    accepted_for_closure = bool_value(
        data,
        "accepted_for_closure",
        "closure.accepted_for_closure",
        "final_phase_acceptance_matrix.accepted_for_closure",
    )
    source_33h_complete = bool_value(data, "source_33h_complete", "source_33h_gate.complete")
    missing_required_phase_count = count_value(
        data,
        "missing_required_phase_count",
        "phase_acceptance.missing_required_phase_count",
        "final_phase_acceptance_matrix.missing_required_phase_count",
        "final_phase_acceptance_matrix.missing_required_phase_tokens",
    )
    rejected_required_phase_count = count_value(
        data,
        "rejected_required_phase_count",
        "phase_acceptance.rejected_required_phase_count",
        "final_phase_acceptance_matrix.rejected_required_phase_count",
        "final_phase_acceptance_matrix.rejected_required_phase_tokens",
    )
    historical_blocking_condition_count = count_value(
        data,
        "blocking_condition_count",
        "closure.blocking_condition_count",
        "next_phase_unlock_plan.blocking_conditions",
    )
    historical_missing_git_tag_count = count_value(data, "missing_git_tag_count", "git_tag_audit.missing_git_tag_count", "git_tag_audit.missing_tags")
    historical_dirty_worktree_count = count_value(data, "dirty_worktree_count", "git_tag_audit.dirty_worktree_count")
    manifest_sha256 = value(data, "manifest_sha256", "source_33h_gate.manifest_sha256")
    immutable_plan_digest = value(data, "immutable_plan_digest", "source_33h_gate.immutable_plan_digest")

    safety_keys = (
        "approved_for_live_real",
        "approved_for_paper_transition",
        "approved_for_exchange_submit",
        "approved_for_runtime_overlay",
        "archive_execution_allowed",
        "archive_move_performed",
        "file_delete_performed",
        "destructive_cleanup_performed",
        "exchange_submit_performed",
        "trading_action_performed",
        "training_performed",
        "reload_performed",
        "runtime_overlay_activated",
        "next_phase_unlock_performed",
    )
    safety_locked = all(
        false_or_missing(data, key, f"safety_snapshot.{key}", f"no_submit_transition_boundary.{key}")
        for key in safety_keys
    )
    complete = (
        status == "READY"
        and decision == SOURCE_33I_DECISION
        and accepted_for_closure
        and source_33h_complete
        and missing_required_phase_count == 0
        and rejected_required_phase_count == 0
        and safety_locked
    )
    return Source33IClosureGate(
        complete=complete,
        report=str(report_path.relative_to(repo_root)),
        status=status,
        decision=decision,
        error=None if complete else "source_33i_closure_gate_not_satisfied",
        accepted_for_closure=accepted_for_closure,
        source_33h_complete=source_33h_complete,
        missing_required_phase_count=missing_required_phase_count,
        rejected_required_phase_count=rejected_required_phase_count,
        historical_blocking_condition_count=historical_blocking_condition_count,
        historical_missing_git_tag_count=historical_missing_git_tag_count,
        historical_dirty_worktree_count=historical_dirty_worktree_count,
        manifest_sha256=str(manifest_sha256) if manifest_sha256 else None,
        immutable_plan_digest=str(immutable_plan_digest) if immutable_plan_digest else None,
    )


def evaluate_git_tags(repo_root: Path) -> GitTagAudit:
    ok_head, head, head_err = run_git(repo_root, ["rev-parse", "--short", "HEAD"])
    if not ok_head:
        return GitTagAudit(
            complete=True,
            git_available=False,
            git_branch=None,
            git_head_short=None,
            current_dirty_worktree_count=0,
            required_tag_count=len(REQUIRED_33_TAGS),
            present_tag_count=0,
            missing_tag_count=0,
            missing_tags=[],
            advisory_only=True,
            error=head_err or "git_not_available",
        )
    ok_branch, branch, _ = run_git(repo_root, ["branch", "--show-current"])
    ok_status, status, _ = run_git(repo_root, ["status", "--short"])
    ok_tags, tags_stdout, tags_err = run_git(repo_root, ["tag", "--list", "4B.4.3.6.6.33*"])
    tags = {line.strip() for line in tags_stdout.splitlines() if line.strip()} if ok_tags else set()
    missing_tags = [tag for tag in REQUIRED_33_TAGS if tag not in tags]
    return GitTagAudit(
        complete=True,
        git_available=True,
        git_branch=branch if ok_branch else None,
        git_head_short=head,
        current_dirty_worktree_count=len([line for line in status.splitlines() if line.strip()]) if ok_status else 0,
        required_tag_count=len(REQUIRED_33_TAGS),
        present_tag_count=len([tag for tag in REQUIRED_33_TAGS if tag in tags]),
        missing_tag_count=len(missing_tags),
        missing_tags=missing_tags,
        advisory_only=True,
        error=None if ok_tags else tags_err,
    )


def build_readiness_scope(source: Source33IClosureGate) -> ReadinessScopeDefinition:
    allowed_scope = [
        "post-recovery readiness scope definition",
        "operator-reviewed no-submit transition boundary documentation",
        "34A acceptance criteria matrix",
        "next-phase planning ledger for 34B",
        "evidence-only reporting under reports/recovery",
    ]
    excluded_scope = [
        "live-real order submission",
        "paper-trading transition approval",
        "exchange or network submit capability",
        "runtime overlay activation",
        "strategy decision logic mutation",
        "model training, model reload, or threshold relaxation",
        "archive execution, file move, or destructive cleanup",
    ]
    payload: dict[str, Any] = {
        "phase": PATCH_VERSION,
        "source_33i_report": source.report,
        "allowed_scope": allowed_scope,
        "explicitly_excluded_scope": excluded_scope,
        "readiness_inputs": [
            "33I closure report READY",
            "33H final no-execution gate locked",
            "33A-33I recovery evidence chain",
        ],
        "readiness_outputs": [
            "34A readiness scope definition",
            "34A no-submit transition boundary",
            "34A acceptance criteria matrix",
        ],
    }
    return ReadinessScopeDefinition(
        complete=True,
        phase=PATCH_VERSION,
        scope_status="READINESS_SCOPE_DEFINED_NO_RUNTIME_MUTATION",
        allowed_scope=allowed_scope,
        explicitly_excluded_scope=excluded_scope,
        readiness_inputs=list(payload["readiness_inputs"]),
        readiness_outputs=list(payload["readiness_outputs"]),
        risk_manager_note="34A is planning-only. It does not authorize paper, live, exchange submit, runtime overlay, training, reload, archive execution, or cleanup.",
        digest=stable_json_digest(payload),
    )


def build_no_submit_boundary() -> NoSubmitTransitionBoundary:
    payload: dict[str, Any] = {
        "boundary_status": "NO_SUBMIT_TRANSITION_BOUNDARY_LOCKED",
        "submit_boundary_relaxed": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "live_real_submit_allowed": False,
        "paper_submit_allowed": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "exchange_submit_performed": False,
        "order_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }
    return NoSubmitTransitionBoundary(complete=True, digest=stable_json_digest(payload), **payload)


def build_acceptance_matrix(source: Source33IClosureGate, scope: ReadinessScopeDefinition, boundary: NoSubmitTransitionBoundary, git_audit: GitTagAudit) -> AcceptanceCriteriaMatrix:
    criteria = [
        AcceptanceCriterion("34A-C01", "33I closure source gate is complete.", True, source.complete, source.report or "missing source 33I report"),
        AcceptanceCriterion("34A-C02", "Readiness scope definition is produced.", True, scope.complete, "readiness_scope_definition_complete"),
        AcceptanceCriterion("34A-C03", "No-submit transition boundary is locked.", True, boundary.complete and not boundary.submit_boundary_relaxed, "no_submit_transition_boundary_complete"),
        AcceptanceCriterion("34A-C04", "No trading, exchange submit, paper/live approval, runtime overlay, reload, training, archive execution, or cleanup is performed.", True, not any([
            boundary.approved_for_live_real,
            boundary.approved_for_paper_transition,
            boundary.approved_for_exchange_submit,
            boundary.approved_for_runtime_overlay,
            boundary.live_real_submit_allowed,
            boundary.paper_submit_allowed,
            boundary.exchange_submit_allowed,
            boundary.network_submit_allowed,
            boundary.runtime_overlay_allowed,
            boundary.exchange_submit_performed,
            boundary.order_submit_performed,
            boundary.trading_action_performed,
            boundary.training_performed,
            boundary.reload_performed,
            boundary.runtime_overlay_activated,
            boundary.archive_execution_allowed,
            boundary.archive_move_performed,
            boundary.file_delete_performed,
            boundary.destructive_cleanup_performed,
            boundary.next_phase_unlock_allowed,
            boundary.next_phase_unlock_performed,
        ]), "all_runtime_action_flags_false"),
        AcceptanceCriterion("34A-C05", "34A acceptance criteria matrix is generated.", True, True, "acceptance_criteria_matrix_complete"),
        AcceptanceCriterion("34A-C06", "Required 33A-33I local tags are visible when git is available.", False, (not git_audit.git_available) or git_audit.missing_tag_count == 0, "git_tag_audit_advisory"),
        AcceptanceCriterion("34A-C07", "Next phase remains locked pending operator review.", True, not boundary.next_phase_unlock_allowed and not boundary.next_phase_unlock_performed, "next_phase_unlock_allowed_false"),
    ]
    required = [item for item in criteria if item.required]
    rejected_required = [item for item in required if not item.satisfied]
    payload = [asdict(item) for item in criteria]
    return AcceptanceCriteriaMatrix(
        complete=len(rejected_required) == 0,
        phase=PATCH_VERSION,
        accepted_criterion_count=len([item for item in criteria if item.satisfied]),
        required_criterion_count=len(required),
        rejected_required_criterion_count=len(rejected_required),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_report(repo_root: Path) -> tuple[
    PostRecoveryNextPhasePlanningReport,
    Source33IClosureGate,
    GitTagAudit,
    ReadinessScopeDefinition,
    NoSubmitTransitionBoundary,
    AcceptanceCriteriaMatrix,
]:
    source = evaluate_source_33i(repo_root)
    git_audit = evaluate_git_tags(repo_root)
    scope = build_readiness_scope(source)
    boundary = build_no_submit_boundary()
    matrix = build_acceptance_matrix(source, scope, boundary, git_audit)
    ok = source.complete and scope.complete and boundary.complete and matrix.complete and not boundary.submit_boundary_relaxed
    report = PostRecoveryNextPhasePlanningReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="post_recovery_next_phase_planning",
        status="READY" if ok else "NOT_READY",
        ok=ok,
        decision=READY_DECISION if ok else NOT_READY_DECISION,
        source_33i_complete=source.complete,
        source_33i_report=source.report,
        source_33i_decision=source.decision,
        accepted_for_closure=source.accepted_for_closure,
        readiness_scope_definition_complete=scope.complete,
        no_submit_transition_boundary_complete=boundary.complete,
        acceptance_criteria_matrix_complete=matrix.complete,
        accepted_criterion_count=matrix.accepted_criterion_count,
        required_criterion_count=matrix.required_criterion_count,
        rejected_required_criterion_count=matrix.rejected_required_criterion_count,
        git_tag_audit_complete=git_audit.complete,
        current_dirty_worktree_count=git_audit.current_dirty_worktree_count,
        missing_git_tag_count=git_audit.missing_tag_count,
        present_git_tag_count=git_audit.present_tag_count,
        next_phase=NEXT_PHASE,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        next_phase_unlock_status="NEXT_PHASE_PLANNED_PENDING_OPERATOR_REVIEW_NO_SUBMIT_BOUNDARY_LOCKED",
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        live_real_submit_allowed=False,
        paper_submit_allowed=False,
        exchange_submit_allowed=False,
        network_submit_allowed=False,
        runtime_overlay_allowed=False,
        exchange_submit_performed=False,
        order_submit_performed=False,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        archive_execution_allowed=False,
        archive_move_performed=False,
        file_delete_performed=False,
        destructive_cleanup_performed=False,
        submit_boundary_relaxed=False,
        readiness_scope_digest=scope.digest,
        no_submit_boundary_digest=boundary.digest,
        acceptance_matrix_digest=matrix.digest,
        manifest_sha256=source.manifest_sha256,
        immutable_plan_digest=source.immutable_plan_digest,
    )
    return report, source, git_audit, scope, boundary, matrix


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run(repo_root: Path, reports_dir: Path) -> PostRecoveryNextPhasePlanningReport:
    report, source, git_audit, scope, boundary, matrix = build_report(repo_root)
    ts = utc_timestamp()
    reports_dir.mkdir(parents=True, exist_ok=True)
    scope_path = reports_dir / f"{PATCH_ID}_readiness_scope_definition_{ts}.json"
    boundary_path = reports_dir / f"{PATCH_ID}_no_submit_transition_boundary_{ts}.json"
    matrix_path = reports_dir / f"{PATCH_ID}_acceptance_criteria_matrix_{ts}.json"
    report_path = reports_dir / f"{PATCH_ID}_post_recovery_next_phase_planning_{ts}_{report.status.lower()}.json"

    write_json(scope_path, asdict(scope))
    write_json(boundary_path, asdict(boundary))
    write_json(matrix_path, asdict(matrix))
    write_json(report_path, asdict(report) | {
        "report_path": str(report_path),
        "readiness_scope_definition_path": str(scope_path),
        "no_submit_transition_boundary_path": str(boundary_path),
        "acceptance_criteria_matrix_path": str(matrix_path),
        "source_33i_gate": asdict(source),
        "git_tag_audit": asdict(git_audit),
    })

    return PostRecoveryNextPhasePlanningReport(
        **(asdict(report) | {
            "report_path": str(report_path),
            "readiness_scope_definition_path": str(scope_path),
            "no_submit_transition_boundary_path": str(boundary_path),
            "acceptance_criteria_matrix_path": str(matrix_path),
        })
    )


def report_to_summary(report: PostRecoveryNextPhasePlanningReport) -> dict[str, Any]:
    return asdict(report)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else repo_root / "reports" / "recovery"
    if args.write:
        report = run(repo_root, reports_dir)
    else:
        report, *_ = build_report(repo_root)

    summary = report_to_summary(report)
    if args.once_json:
        print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
