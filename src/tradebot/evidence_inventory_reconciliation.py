from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436634B"
PATCH_VERSION = "4B.4.3.6.6.34B"
PATCH_NAME = "Evidence Inventory Reconciliation"
READY_DECISION = "EVIDENCE_INVENTORY_RECONCILIATION_READY_POST_34A_BASELINE_LOCKED"
NOT_READY_DECISION = "EVIDENCE_INVENTORY_RECONCILIATION_NOT_READY"
SOURCE_34A_DECISION = "POST_RECOVERY_NEXT_PHASE_PLANNING_READY_NO_SUBMIT_BOUNDARY_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.34C"
RECOVERY_REPORT_TS_RE = re.compile(r"_(?P<ts>\d{8}T\d{6}Z)(?:_(?P<status>ready|not_ready))?\.json$")


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
class Source34APlanningGate:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    source_33i_complete: bool
    accepted_for_closure: bool
    readiness_scope_definition_complete: bool
    no_submit_transition_boundary_complete: bool
    acceptance_criteria_matrix_complete: bool
    rejected_required_criterion_count: int
    submit_boundary_relaxed: bool
    manifest_sha256: str | None
    immutable_plan_digest: str | None


@dataclass(frozen=True)
class DeduplicationGroup:
    group_id: str
    report_count: int
    latest_report: str
    latest_timestamp: str | None
    stale_report_count: int
    stale_reports: list[str]
    status_tokens: list[str]


@dataclass(frozen=True)
class RecoveryReportDeduplicationLedger:
    complete: bool
    scanned_report_count: int
    logical_group_count: int
    duplicate_group_count: int
    duplicate_report_count: int
    latest_report_count: int
    stale_report_count: int
    deletion_recommended: bool
    deletion_performed: bool
    groups: list[DeduplicationGroup]
    digest: str


@dataclass(frozen=True)
class DirtyWorktreeRecord:
    raw_status: str
    path: str
    category: str
    advisory_only: bool
    current_phase_artifact: bool


@dataclass(frozen=True)
class AdvisoryDirtyWorktreeNormalizer:
    complete: bool
    git_available: bool
    current_dirty_worktree_count: int
    normalized_dirty_worktree_count: int
    blocker_count: int
    advisory_only: bool
    categories: dict[str, int]
    records: list[DirtyWorktreeRecord]
    error: str | None
    digest: str


@dataclass(frozen=True)
class Post34AEvidenceBaseline:
    complete: bool
    baseline_status: str
    source_34a_report: str | None
    total_recovery_report_count: int
    ready_report_count: int
    not_ready_report_count: int
    unknown_report_count: int
    duplicate_group_count: int
    duplicate_report_count: int
    dirty_worktree_advisory_count: int
    no_submit_boundary_locked: bool
    next_phase: str
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    digest: str


@dataclass(frozen=True)
class EvidenceInventoryReconciliationReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_34a_complete: bool
    source_34a_report: str | None
    source_34a_decision: str | None
    recovery_report_deduplication_complete: bool
    recovery_report_scanned_count: int
    duplicate_group_count: int
    duplicate_report_count: int
    deduplication_action_performed: bool
    advisory_dirty_worktree_normalizer_complete: bool
    current_dirty_worktree_count: int
    normalized_dirty_worktree_count: int
    dirty_worktree_blocker_count: int
    dirty_worktree_advisory_only: bool
    post_34a_evidence_baseline_complete: bool
    ready_report_count: int
    not_ready_report_count: int
    unknown_report_count: int
    baseline_digest: str | None
    deduplication_digest: str | None
    dirty_worktree_digest: str | None
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
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    report_path: str | None = None
    recovery_report_deduplication_path: str | None = None
    advisory_dirty_worktree_normalizer_path: str | None = None
    post_34a_evidence_baseline_path: str | None = None


def parse_source_34a_gate(repo_root: Path) -> Source34APlanningGate:
    report_path = find_latest_report(repo_root, "4B436634A_post_recovery_next_phase_planning_*_ready.json")
    if report_path is None:
        return Source34APlanningGate(False, None, None, None, "missing_34a_ready_report", False, False, False, False, False, 0, False, None, None)
    data, error = read_json(report_path)
    rel = relative_to_repo(repo_root, report_path)
    if data is None:
        return Source34APlanningGate(False, rel, None, None, error, False, False, False, False, False, 0, False, None, None)

    status = str(value(data, "status", default=""))
    decision = str(value(data, "decision", default=""))
    source_33i_complete = bool_value(data, "source_33i_complete", "source_33i_gate.complete")
    accepted_for_closure = bool_value(data, "accepted_for_closure", "acceptance_criteria_matrix.accepted_for_closure")
    readiness_complete = bool_value(data, "readiness_scope_definition_complete", "readiness_scope_definition.complete")
    boundary_complete = bool_value(data, "no_submit_transition_boundary_complete", "no_submit_transition_boundary.complete")
    matrix_complete = bool_value(data, "acceptance_criteria_matrix_complete", "acceptance_criteria_matrix.complete")
    rejected_count = int_value(data, "rejected_required_criterion_count", "acceptance_criteria_matrix.rejected_required_criterion_count")
    submit_boundary_relaxed = bool_value(data, "submit_boundary_relaxed", "no_submit_transition_boundary.submit_boundary_relaxed")
    manifest_sha256 = value(data, "manifest_sha256", "source_33i_gate.manifest_sha256")
    immutable_plan_digest = value(data, "immutable_plan_digest", "source_33i_gate.immutable_plan_digest")

    safety_ok = all(
        false_or_missing(data, path, f"no_submit_transition_boundary.{path}")
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
        )
    )

    complete = (
        status == "READY"
        and decision == SOURCE_34A_DECISION
        and source_33i_complete
        and accepted_for_closure
        and readiness_complete
        and boundary_complete
        and matrix_complete
        and rejected_count == 0
        and not submit_boundary_relaxed
        and safety_ok
    )
    return Source34APlanningGate(
        complete=complete,
        report=rel,
        status=status or None,
        decision=decision or None,
        error=None if complete else "source_34a_gate_not_complete",
        source_33i_complete=source_33i_complete,
        accepted_for_closure=accepted_for_closure,
        readiness_scope_definition_complete=readiness_complete,
        no_submit_transition_boundary_complete=boundary_complete,
        acceptance_criteria_matrix_complete=matrix_complete,
        rejected_required_criterion_count=rejected_count,
        submit_boundary_relaxed=submit_boundary_relaxed,
        manifest_sha256=str(manifest_sha256) if manifest_sha256 is not None else None,
        immutable_plan_digest=str(immutable_plan_digest) if immutable_plan_digest is not None else None,
    )


def report_group_id(path: Path) -> tuple[str, str | None, str | None]:
    name = path.name
    match = RECOVERY_REPORT_TS_RE.search(name)
    if not match:
        return path.stem, None, None
    return name[: match.start()], match.group("ts"), match.group("status")


def build_recovery_report_deduplication(repo_root: Path) -> RecoveryReportDeduplicationLedger:
    reports_dir = repo_root / "reports" / "recovery"
    files = sorted(path for path in reports_dir.glob("*.json") if path.is_file())
    grouped: dict[str, list[tuple[Path, str | None, str | None]]] = {}
    for path in files:
        gid, ts, status = report_group_id(path)
        grouped.setdefault(gid, []).append((path, ts, status))

    groups: list[DeduplicationGroup] = []
    duplicate_report_count = 0
    for gid in sorted(grouped):
        records = sorted(grouped[gid], key=lambda item: (item[1] or "", item[0].name))
        latest_path, latest_ts, _ = records[-1]
        stale = records[:-1]
        duplicate_report_count += len(stale)
        groups.append(
            DeduplicationGroup(
                group_id=gid,
                report_count=len(records),
                latest_report=relative_to_repo(repo_root, latest_path),
                latest_timestamp=latest_ts,
                stale_report_count=len(stale),
                stale_reports=[relative_to_repo(repo_root, item[0]) for item in stale],
                status_tokens=sorted({str(item[2]) for item in records if item[2] is not None}),
            )
        )

    duplicate_groups = [group for group in groups if group.report_count > 1]
    payload = {
        "groups": [asdict(group) for group in groups],
        "scanned_report_count": len(files),
        "logical_group_count": len(groups),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_report_count": duplicate_report_count,
        "deletion_recommended": False,
        "deletion_performed": False,
    }
    return RecoveryReportDeduplicationLedger(
        complete=True,
        scanned_report_count=len(files),
        logical_group_count=len(groups),
        duplicate_group_count=len(duplicate_groups),
        duplicate_report_count=duplicate_report_count,
        latest_report_count=len(groups),
        stale_report_count=duplicate_report_count,
        deletion_recommended=False,
        deletion_performed=False,
        groups=groups,
        digest=stable_json_digest(payload),
    )


def classify_dirty_path(path: str) -> tuple[str, bool]:
    normalized = path.replace("\\", "/")
    current_phase = "4B436634B" in normalized or "34B" in normalized
    if "__pycache__/" in normalized or normalized.endswith(".pyc"):
        return "python_cache", current_phase
    if ".pytest_cache" in normalized:
        return "pytest_cache", current_phase
    if "/_patch_backup_" in normalized or normalized.startswith("tools/_patch_backup_"):
        return "patch_backup", current_phase
    if "/_patch_payload_" in normalized or normalized.startswith("tools/_patch_payload_"):
        return "patch_payload", current_phase
    if normalized.startswith("reports/recovery/"):
        return "recovery_evidence_report", current_phase
    if normalized.startswith("docs/"):
        return "documentation", current_phase
    if normalized.startswith("tests/"):
        return "test_artifact", current_phase
    if normalized.startswith("tools/"):
        return "tooling", current_phase
    if normalized.startswith("src/"):
        return "source_artifact", current_phase
    if normalized.startswith("README"):
        return "readme", current_phase
    return "other", current_phase


def parse_git_status_line(line: str) -> tuple[str, str]:
    raw_status = line[:2].strip() or "?"
    raw_path = line[3:] if len(line) > 3 else ""
    if " -> " in raw_path:
        raw_path = raw_path.split(" -> ", 1)[1]
    return raw_status, raw_path.strip()


def build_dirty_worktree_normalizer(repo_root: Path) -> AdvisoryDirtyWorktreeNormalizer:
    ok, stdout, stderr = run_git(repo_root, ["status", "--short"])
    if not ok:
        payload = {"git_available": False, "error": stderr or "git_status_failed", "records": []}
        return AdvisoryDirtyWorktreeNormalizer(True, False, 0, 0, 0, True, {}, [], stderr or "git_status_failed", stable_json_digest(payload))

    records: list[DirtyWorktreeRecord] = []
    categories: dict[str, int] = {}
    for line in stdout.splitlines():
        if not line.strip():
            continue
        raw_status, path = parse_git_status_line(line)
        category, current_phase = classify_dirty_path(path)
        categories[category] = categories.get(category, 0) + 1
        records.append(DirtyWorktreeRecord(raw_status, path, category, True, current_phase))

    payload = {"records": [asdict(record) for record in records], "categories": categories, "advisory_only": True, "blocker_count": 0}
    return AdvisoryDirtyWorktreeNormalizer(
        complete=True,
        git_available=True,
        current_dirty_worktree_count=len(records),
        normalized_dirty_worktree_count=len(records),
        blocker_count=0,
        advisory_only=True,
        categories=dict(sorted(categories.items())),
        records=records,
        error=None,
        digest=stable_json_digest(payload),
    )


def count_report_statuses(repo_root: Path) -> tuple[int, int, int, int]:
    reports_dir = repo_root / "reports" / "recovery"
    total = ready = not_ready = unknown = 0
    for path in reports_dir.glob("*.json"):
        if not path.is_file():
            continue
        total += 1
        name = path.name.lower()
        if name.endswith("_ready.json"):
            ready += 1
        elif name.endswith("_not_ready.json"):
            not_ready += 1
        else:
            data, _ = read_json(path)
            status = str(value(data or {}, "status", default="")).upper() if data else ""
            if status == "READY":
                ready += 1
            elif status == "NOT_READY":
                not_ready += 1
            else:
                unknown += 1
    return total, ready, not_ready, unknown


def build_post_34a_baseline(repo_root: Path, source: Source34APlanningGate, dedup: RecoveryReportDeduplicationLedger, dirty: AdvisoryDirtyWorktreeNormalizer) -> Post34AEvidenceBaseline:
    total, ready, not_ready, unknown = count_report_statuses(repo_root)
    payload = {
        "source_34a_report": source.report,
        "source_34a_complete": source.complete,
        "total_recovery_report_count": total,
        "ready_report_count": ready,
        "not_ready_report_count": not_ready,
        "unknown_report_count": unknown,
        "duplicate_group_count": dedup.duplicate_group_count,
        "duplicate_report_count": dedup.duplicate_report_count,
        "dirty_worktree_advisory_count": dirty.current_dirty_worktree_count,
        "no_submit_boundary_locked": True,
        "next_phase": NEXT_PHASE,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }
    return Post34AEvidenceBaseline(
        complete=source.complete and dedup.complete and dirty.complete,
        baseline_status="POST_34A_BASELINE_READY_NO_ACTIONS" if source.complete else "POST_34A_BASELINE_BLOCKED_BY_SOURCE_34A",
        source_34a_report=source.report,
        total_recovery_report_count=total,
        ready_report_count=ready,
        not_ready_report_count=not_ready,
        unknown_report_count=unknown,
        duplicate_group_count=dedup.duplicate_group_count,
        duplicate_report_count=dedup.duplicate_report_count,
        dirty_worktree_advisory_count=dirty.current_dirty_worktree_count,
        no_submit_boundary_locked=True,
        next_phase=NEXT_PHASE,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        digest=stable_json_digest(payload),
    )


def build_report(repo_root: Path, write: bool = False, reports_dir: Path | None = None) -> EvidenceInventoryReconciliationReport:
    source = parse_source_34a_gate(repo_root)
    dedup = build_recovery_report_deduplication(repo_root)
    dirty = build_dirty_worktree_normalizer(repo_root)
    baseline = build_post_34a_baseline(repo_root, source, dedup, dirty)

    safety_ok = True
    ok = bool(source.complete and dedup.complete and dirty.complete and baseline.complete and safety_ok)
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    report = EvidenceInventoryReconciliationReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="evidence_inventory_reconciliation",
        status=status,
        ok=ok,
        decision=decision,
        source_34a_complete=source.complete,
        source_34a_report=source.report,
        source_34a_decision=source.decision,
        recovery_report_deduplication_complete=dedup.complete,
        recovery_report_scanned_count=dedup.scanned_report_count,
        duplicate_group_count=dedup.duplicate_group_count,
        duplicate_report_count=dedup.duplicate_report_count,
        deduplication_action_performed=False,
        advisory_dirty_worktree_normalizer_complete=dirty.complete,
        current_dirty_worktree_count=dirty.current_dirty_worktree_count,
        normalized_dirty_worktree_count=dirty.normalized_dirty_worktree_count,
        dirty_worktree_blocker_count=dirty.blocker_count,
        dirty_worktree_advisory_only=dirty.advisory_only,
        post_34a_evidence_baseline_complete=baseline.complete,
        ready_report_count=baseline.ready_report_count,
        not_ready_report_count=baseline.not_ready_report_count,
        unknown_report_count=baseline.unknown_report_count,
        baseline_digest=baseline.digest,
        deduplication_digest=dedup.digest,
        dirty_worktree_digest=dirty.digest,
        next_phase=NEXT_PHASE,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        next_phase_unlock_status="NEXT_PHASE_34C_BLOCKED_PENDING_OPERATOR_REVIEW_NO_SUBMIT_BOUNDARY_LOCKED",
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
        manifest_sha256=source.manifest_sha256,
        immutable_plan_digest=source.immutable_plan_digest,
    )

    if not write:
        return report

    out_dir = reports_dir or (repo_root / "reports" / "recovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_timestamp()
    suffix = status.lower()
    dedup_path = out_dir / f"{PATCH_ID}_recovery_report_deduplication_{ts}.json"
    dirty_path = out_dir / f"{PATCH_ID}_advisory_dirty_worktree_normalizer_{ts}.json"
    baseline_path = out_dir / f"{PATCH_ID}_post_34a_evidence_baseline_{ts}.json"
    report_path = out_dir / f"{PATCH_ID}_evidence_inventory_reconciliation_{ts}_{suffix}.json"

    dedup_path.write_text(json.dumps(asdict(dedup), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    dirty_path.write_text(json.dumps(asdict(dirty), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    baseline_path.write_text(json.dumps(asdict(baseline), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    final_report = EvidenceInventoryReconciliationReport(
        **{
            **asdict(report),
            "report_path": str(report_path),
            "recovery_report_deduplication_path": str(dedup_path),
            "advisory_dirty_worktree_normalizer_path": str(dirty_path),
            "post_34a_evidence_baseline_path": str(baseline_path),
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
