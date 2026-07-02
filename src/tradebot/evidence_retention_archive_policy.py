from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

PATCH_ID = "4B436633F"
PATCH_VERSION = "4B.4.3.6.6.33F"
PATCH_NAME = "Evidence Retention & Archive Policy"
READY_DECISION = "EVIDENCE_RETENTION_ARCHIVE_POLICY_READY_NON_DESTRUCTIVE_PLAN_COMPLETE"
NOT_READY_DECISION = "EVIDENCE_RETENTION_ARCHIVE_POLICY_NOT_READY"

Status = Literal["READY", "NOT_READY"]

_REPORT_TS_RE = re.compile(r"_20\d{6}T\d{6}Z")
_PATCH_TOKEN_RE = re.compile(r"4B4366\d{2,3}[A-Z](?:[_-]H\d+)?", re.IGNORECASE)


@dataclass(slots=True)
class Source33EStatus:
    complete: bool
    report_path: str
    status: str | None
    decision: str | None
    source_33d_complete: bool
    status_conflict_resolution_complete: bool
    unknown_evidence_triage_complete: bool
    malformed_json_triage_complete: bool
    unresolved_conflict_count: int | None
    residual_unknown_count: int | None
    error: str | None = None


@dataclass(slots=True)
class RetentionRule:
    rule_id: str
    selector: str
    action: str
    rationale: str
    retention_class: str
    destructive: bool = False


@dataclass(slots=True)
class EvidenceAssetRecord:
    path: str
    asset_type: str
    retention_class: str
    recommended_action: str
    reason: str
    size_bytes: int
    modified_at_epoch_ms: int
    phase_token: str | None = None
    status_hint: str | None = None
    family_key: str | None = None
    age_days: float | None = None


@dataclass(slots=True)
class ReportRetentionSummary:
    complete: bool
    scanned_report_count: int
    latest_ready_report_count: int
    historical_ready_report_count: int
    not_ready_report_count: int
    ledger_report_count: int
    unknown_report_count: int
    records: list[EvidenceAssetRecord] = field(default_factory=list)


@dataclass(slots=True)
class BackupPayloadArchiveManifest:
    complete: bool
    backup_dir_count: int
    payload_dir_count: int
    legacy_patch_dir_count: int
    manifest_record_count: int
    records: list[EvidenceAssetRecord] = field(default_factory=list)


@dataclass(slots=True)
class NonDestructiveCleanupPlan:
    complete: bool
    destructive_cleanup_performed: bool
    candidate_count: int
    pycache_candidate_count: int
    pytest_cache_candidate_count: int
    duplicate_attempt_report_count: int
    cleanup_records: list[EvidenceAssetRecord] = field(default_factory=list)


@dataclass(slots=True)
class EvidenceAgingLedger:
    complete: bool
    total_record_count: int
    hot_count: int
    warm_count: int
    cold_count: int
    archive_candidate_count: int
    records: list[EvidenceAssetRecord] = field(default_factory=list)


@dataclass(slots=True)
class SafetySnapshot:
    approved_for_live_real: bool = False
    approved_for_paper_transition: bool = False
    approved_for_exchange_submit: bool = False
    approved_for_runtime_overlay: bool = False
    live_real_submit_allowed: bool = False
    paper_submit_allowed: bool = False
    network_submit_allowed: bool = False
    exchange_submit_allowed: bool = False
    runtime_overlay_allowed: bool = False
    trading_action_performed: bool = False
    training_performed: bool = False
    reload_performed: bool = False
    exchange_submit_performed: bool = False
    runtime_overlay_activated: bool = False
    destructive_cleanup_performed: bool = False


@dataclass(slots=True)
class EvidenceRetentionArchivePolicyReport:
    patch_id: str
    patch_version: str
    patch_name: str
    status: Status
    decision: str
    generated_at_epoch_ms: int
    source_33e: Source33EStatus
    retention_rules_complete: bool
    report_retention: ReportRetentionSummary
    backup_payload_archive_manifest: BackupPayloadArchiveManifest
    non_destructive_cleanup_plan: NonDestructiveCleanupPlan
    evidence_aging_ledger: EvidenceAgingLedger
    safety_snapshot: SafetySnapshot
    recommended_next_phase: str

    @property
    def ok(self) -> bool:
        return self.status == "READY"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = self.ok
        payload["approved_for_live_real"] = self.safety_snapshot.approved_for_live_real
        payload["approved_for_paper_transition"] = self.safety_snapshot.approved_for_paper_transition
        payload["approved_for_exchange_submit"] = self.safety_snapshot.approved_for_exchange_submit
        payload["approved_for_runtime_overlay"] = self.safety_snapshot.approved_for_runtime_overlay
        payload["trading_action_performed"] = self.safety_snapshot.trading_action_performed
        payload["training_performed"] = self.safety_snapshot.training_performed
        payload["reload_performed"] = self.safety_snapshot.reload_performed
        payload["exchange_submit_performed"] = self.safety_snapshot.exchange_submit_performed
        payload["runtime_overlay_activated"] = self.safety_snapshot.runtime_overlay_activated
        payload["destructive_cleanup_performed"] = self.safety_snapshot.destructive_cleanup_performed
        return payload


def _now_ms() -> int:
    return int(time.time() * 1000)


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"json_decode_error:{exc.msg}"
    except OSError as exc:
        return None, f"os_error:{exc}"
    if not isinstance(payload, dict):
        return None, "non_object_root"
    return payload, None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "ready", "complete"}
    return bool(value)


def _latest(paths: Iterable[Path]) -> Path | None:
    found = list(paths)
    if not found:
        return None
    return max(found, key=lambda p: (p.stat().st_mtime_ns, p.as_posix()))


def find_source_33e_status(repo_root: Path) -> Source33EStatus:
    """Resolve the latest 33E READY source report.

    33E-H1 can emit a full run report with nested sections. 33F-H1
    accepts both the top-level check-summary shape and the nested run-report
    shape while remaining fail-closed for missing, malformed, not READY, or
    unresolved-conflict sources.
    """
    reports_dir = repo_root / "reports" / "recovery"
    ready_candidates = [
        path for path in reports_dir.glob("4B436633E_status_conflict_resolver_*_ready.json")
        if "_not_ready" not in path.name.lower()
    ]
    all_candidates = list(reports_dir.glob("4B436633E_status_conflict_resolver_*.json"))
    source = _latest(ready_candidates) or _latest(all_candidates)
    if source is None:
        return Source33EStatus(
            complete=False,
            report_path="",
            status=None,
            decision=None,
            source_33d_complete=False,
            status_conflict_resolution_complete=False,
            unknown_evidence_triage_complete=False,
            malformed_json_triage_complete=False,
            unresolved_conflict_count=None,
            residual_unknown_count=None,
            error="source_33e_report_not_found",
        )

    payload, error = _read_json_object(source)
    if payload is None:
        return Source33EStatus(
            complete=False,
            report_path=_rel(source, repo_root),
            status=None,
            decision=None,
            source_33d_complete=False,
            status_conflict_resolution_complete=False,
            unknown_evidence_triage_complete=False,
            malformed_json_triage_complete=False,
            unresolved_conflict_count=None,
            residual_unknown_count=None,
            error=error,
        )

    def _nested_bool(top_level_key: str, section_key: str | None = None, nested_key: str = "complete") -> bool:
        if top_level_key in payload:
            return _coerce_bool(payload.get(top_level_key))
        if section_key:
            section = payload.get(section_key)
            if isinstance(section, dict) and nested_key in section:
                return _coerce_bool(section.get(nested_key))
        return False

    def _nested_int(top_level_key: str, section_key: str | None = None, nested_key: str | None = None) -> int | None:
        value = payload.get(top_level_key)
        if value is None and section_key and nested_key:
            section = payload.get(section_key)
            if isinstance(section, dict):
                value = section.get(nested_key)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    status = str(payload.get("status") or "")
    decision = str(payload.get("decision") or "")

    source_33d_complete = _nested_bool("source_33d_complete", "source_gate")
    status_conflict_complete = _nested_bool("status_conflict_resolution_complete", "status_conflict_summary")
    unknown_complete = _nested_bool("unknown_evidence_triage_complete", "unknown_evidence_summary")
    malformed_complete = _nested_bool("malformed_json_triage_complete", "malformed_json_summary")

    unresolved_int = _nested_int("unresolved_conflict_count", "status_conflict_summary", "unresolved_conflict_count")
    residual_int = _nested_int("residual_unknown_count", "unknown_evidence_summary", "residual_unknown_count")

    source_gate = payload.get("source_gate")
    if not source_33d_complete and isinstance(source_gate, dict):
        source_33d_complete = _coerce_bool(source_gate.get("source_33d_runtime_safety_lockdown_complete"))

    complete = (
        status.upper() == "READY"
        and decision == "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE"
        and source_33d_complete
        and status_conflict_complete
        and unknown_complete
        and malformed_complete
        and (unresolved_int is None or unresolved_int == 0)
    )

    return Source33EStatus(
        complete=complete,
        report_path=_rel(source, repo_root),
        status=status or None,
        decision=decision or None,
        source_33d_complete=source_33d_complete,
        status_conflict_resolution_complete=status_conflict_complete,
        unknown_evidence_triage_complete=unknown_complete,
        malformed_json_triage_complete=malformed_complete,
        unresolved_conflict_count=unresolved_int,
        residual_unknown_count=residual_int,
        error=None if complete else "source_33e_report_not_complete",
    )

def default_retention_rules() -> list[RetentionRule]:
    return [
        RetentionRule(
            rule_id="REPORT_LATEST_READY_KEEP_IMMUTABLE",
            selector="reports/recovery/*_ready.json latest per family",
            action="retain",
            rationale="Latest READY evidence is promotion-chain proof and must remain immutable.",
            retention_class="canonical_ready_evidence",
        ),
        RetentionRule(
            rule_id="REPORT_HISTORICAL_READY_KEEP_AUDIT",
            selector="reports/recovery/*_ready.json historical",
            action="retain",
            rationale="Historical READY evidence supports audit traceability.",
            retention_class="historical_ready_evidence",
        ),
        RetentionRule(
            rule_id="REPORT_NOT_READY_ARCHIVE_CANDIDATE",
            selector="reports/recovery/*_not_ready.json",
            action="archive_candidate_only",
            rationale="Failed attempts are retained for forensic review but can be moved to cold archive later.",
            retention_class="failed_attempt_evidence",
        ),
        RetentionRule(
            rule_id="LEDGER_KEEP_AUDIT",
            selector="reports/recovery/*ledger*.json",
            action="retain",
            rationale="Ledgers are derived audit indexes and should remain available until a formal archive pass.",
            retention_class="derived_audit_ledger",
        ),
        RetentionRule(
            rule_id="PATCH_BACKUP_ARCHIVE_MANIFEST_ONLY",
            selector="tools/_patch_backup_*",
            action="archive_manifest_only",
            rationale="Backups are not deleted by this patch; manifest provides operator review before archival.",
            retention_class="patch_backup_archive_candidate",
        ),
        RetentionRule(
            rule_id="PATCH_PAYLOAD_ARCHIVE_MANIFEST_ONLY",
            selector="tools/_patch_payload_*",
            action="archive_manifest_only",
            rationale="Payload remnants are not deleted by this patch; manifest provides operator review before archival.",
            retention_class="patch_payload_archive_candidate",
        ),
        RetentionRule(
            rule_id="CACHE_CLEANUP_PLAN_ONLY",
            selector="**/__pycache__, **/.pytest_cache",
            action="cleanup_plan_only",
            rationale="Runtime caches are removable operational noise, but this patch only reports candidates.",
            retention_class="operational_cache_cleanup_candidate",
        ),
    ]


def _family_key(path: Path) -> str:
    name = path.name
    name = _REPORT_TS_RE.sub("_TIMESTAMP", name)
    name = re.sub(r"_(ready|not_ready|approval_required|execution_evidence_required)\.json$", r"_STATUS.json", name, flags=re.I)
    return name


def _status_hint(path: Path, payload: dict[str, Any] | None) -> str:
    lowered = path.name.lower()
    for status in ("execution_evidence_required", "approval_required", "not_ready", "ready"):
        if f"_{status}" in lowered:
            return status
    if payload:
        for key in ("status", "decision", "baseline_status", "baseline_decision", "result"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                text = value.lower()
                if "not_ready" in text or text == "not ready":
                    return "not_ready"
                if "ready" in text:
                    return "ready"
                if "approval" in text:
                    return "approval_required"
                if "execution_evidence" in text:
                    return "execution_evidence_required"
    return "unknown"


def _phase_token(path: Path) -> str | None:
    match = _PATCH_TOKEN_RE.search(path.as_posix())
    return match.group(0).upper().replace("-", "_") if match else None


def _asset_record(
    path: Path,
    repo_root: Path,
    asset_type: str,
    retention_class: str,
    recommended_action: str,
    reason: str,
    status_hint: str | None = None,
    family_key: str | None = None,
) -> EvidenceAssetRecord:
    stat = path.stat()
    age_days = max(0.0, (_now_ms() - int(stat.st_mtime * 1000)) / 86_400_000.0)
    return EvidenceAssetRecord(
        path=_rel(path, repo_root),
        asset_type=asset_type,
        retention_class=retention_class,
        recommended_action=recommended_action,
        reason=reason,
        size_bytes=int(stat.st_size),
        modified_at_epoch_ms=int(stat.st_mtime * 1000),
        phase_token=_phase_token(path),
        status_hint=status_hint,
        family_key=family_key,
        age_days=round(age_days, 4),
    )


def build_report_retention(repo_root: Path) -> ReportRetentionSummary:
    reports_root = repo_root / "reports"
    json_files = sorted(reports_root.rglob("*.json")) if reports_root.exists() else []
    payload_by_path: dict[Path, dict[str, Any] | None] = {}
    status_by_path: dict[Path, str] = {}
    family_by_path: dict[Path, str] = {}
    for path in json_files:
        payload, _error = _read_json_object(path)
        payload_by_path[path] = payload
        status_by_path[path] = _status_hint(path, payload)
        family_by_path[path] = _family_key(path)

    latest_ready: set[Path] = set()
    ready_by_family: dict[str, list[Path]] = {}
    for path in json_files:
        if status_by_path[path] == "ready":
            ready_by_family.setdefault(family_by_path[path], []).append(path)
    for paths in ready_by_family.values():
        latest = _latest(paths)
        if latest is not None:
            latest_ready.add(latest)

    records: list[EvidenceAssetRecord] = []
    latest_ready_count = historical_ready_count = not_ready_count = ledger_count = unknown_count = 0
    for path in json_files:
        status = status_by_path[path]
        family = family_by_path[path]
        name_l = path.name.lower()
        if "ledger" in name_l:
            ledger_count += 1
            rec_class = "derived_audit_ledger"
            action = "retain"
            reason = "derived audit ledger"
        elif status == "ready" and path in latest_ready:
            latest_ready_count += 1
            rec_class = "canonical_ready_evidence"
            action = "retain"
            reason = "latest READY report for family"
        elif status == "ready":
            historical_ready_count += 1
            rec_class = "historical_ready_evidence"
            action = "retain"
            reason = "historical READY report"
        elif status == "not_ready":
            not_ready_count += 1
            rec_class = "failed_attempt_evidence"
            action = "archive_candidate_only"
            reason = "NOT_READY attempt retained for forensic trace"
        elif status in {"approval_required", "execution_evidence_required"}:
            rec_class = "blocked_gate_evidence"
            action = "retain"
            reason = f"blocking gate report: {status}"
        else:
            unknown_count += 1
            rec_class = "unclassified_report_evidence"
            action = "retain_pending_triage"
            reason = "no deterministic report status found"
        records.append(
            _asset_record(
                path=path,
                repo_root=repo_root,
                asset_type="report_json",
                retention_class=rec_class,
                recommended_action=action,
                reason=reason,
                status_hint=status,
                family_key=family,
            )
        )
    return ReportRetentionSummary(
        complete=True,
        scanned_report_count=len(json_files),
        latest_ready_report_count=latest_ready_count,
        historical_ready_report_count=historical_ready_count,
        not_ready_report_count=not_ready_count,
        ledger_report_count=ledger_count,
        unknown_report_count=unknown_count,
        records=records,
    )


def _iter_dirs(repo_root: Path, patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(path for path in repo_root.glob(pattern) if path.is_dir())
    return sorted(set(found), key=lambda p: p.as_posix())


def _dir_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def _dir_record(path: Path, repo_root: Path, asset_type: str, retention_class: str, action: str, reason: str) -> EvidenceAssetRecord:
    stat = path.stat()
    age_days = max(0.0, (_now_ms() - int(stat.st_mtime * 1000)) / 86_400_000.0)
    return EvidenceAssetRecord(
        path=_rel(path, repo_root),
        asset_type=asset_type,
        retention_class=retention_class,
        recommended_action=action,
        reason=reason,
        size_bytes=_dir_size(path),
        modified_at_epoch_ms=int(stat.st_mtime * 1000),
        phase_token=_phase_token(path),
        status_hint=None,
        family_key=None,
        age_days=round(age_days, 4),
    )


def build_backup_payload_archive_manifest(repo_root: Path) -> BackupPayloadArchiveManifest:
    backup_dirs = _iter_dirs(repo_root, ["tools/_patch_backup_*", "_patch_backup_*", "**/_patch_backup_*"])
    payload_dirs = _iter_dirs(repo_root, ["tools/_patch_payload_*", "_patch_payload_*", "**/_patch_payload_*"])
    legacy_dirs = _iter_dirs(repo_root, ["legacy_patches", "tools/legacy_patches", "**/legacy_patches"])
    records: list[EvidenceAssetRecord] = []
    for path in backup_dirs:
        records.append(_dir_record(path, repo_root, "patch_backup_dir", "patch_backup_archive_candidate", "archive_manifest_only", "backup directory requires operator-approved archive pass"))
    for path in payload_dirs:
        records.append(_dir_record(path, repo_root, "patch_payload_dir", "patch_payload_archive_candidate", "archive_manifest_only", "payload directory requires operator-approved archive pass"))
    for path in legacy_dirs:
        records.append(_dir_record(path, repo_root, "legacy_patch_dir", "legacy_patch_archive_candidate", "archive_manifest_only", "legacy patch directory requires operator-approved archive pass"))
    return BackupPayloadArchiveManifest(
        complete=True,
        backup_dir_count=len(backup_dirs),
        payload_dir_count=len(payload_dirs),
        legacy_patch_dir_count=len(legacy_dirs),
        manifest_record_count=len(records),
        records=records,
    )


def build_non_destructive_cleanup_plan(repo_root: Path, report_retention: ReportRetentionSummary) -> NonDestructiveCleanupPlan:
    pycache_dirs = _iter_dirs(repo_root, ["**/__pycache__"])
    pytest_cache_dirs = _iter_dirs(repo_root, [".pytest_cache", "**/.pytest_cache"])
    cleanup_records: list[EvidenceAssetRecord] = []
    for path in pycache_dirs:
        cleanup_records.append(_dir_record(path, repo_root, "pycache_dir", "operational_cache_cleanup_candidate", "cleanup_plan_only", "Python bytecode cache; safe candidate after operator review"))
    for path in pytest_cache_dirs:
        cleanup_records.append(_dir_record(path, repo_root, "pytest_cache_dir", "operational_cache_cleanup_candidate", "cleanup_plan_only", "pytest cache; safe candidate after operator review"))

    duplicate_attempts = [
        record for record in report_retention.records
        if record.retention_class == "failed_attempt_evidence" and record.recommended_action == "archive_candidate_only"
    ]
    cleanup_records.extend(duplicate_attempts)
    return NonDestructiveCleanupPlan(
        complete=True,
        destructive_cleanup_performed=False,
        candidate_count=len(cleanup_records),
        pycache_candidate_count=len(pycache_dirs),
        pytest_cache_candidate_count=len(pytest_cache_dirs),
        duplicate_attempt_report_count=len(duplicate_attempts),
        cleanup_records=cleanup_records,
    )


def build_evidence_aging_ledger(*groups: Iterable[EvidenceAssetRecord]) -> EvidenceAgingLedger:
    records: list[EvidenceAssetRecord] = []
    seen: set[str] = set()
    for group in groups:
        for record in group:
            if record.path in seen:
                continue
            seen.add(record.path)
            records.append(record)
    hot = warm = cold = archive = 0
    for record in records:
        age = record.age_days or 0.0
        if age <= 7:
            hot += 1
        elif age <= 90:
            warm += 1
        else:
            cold += 1
        if record.recommended_action in {"archive_candidate_only", "archive_manifest_only"} or age > 90:
            archive += 1
    return EvidenceAgingLedger(
        complete=True,
        total_record_count=len(records),
        hot_count=hot,
        warm_count=warm,
        cold_count=cold,
        archive_candidate_count=archive,
        records=sorted(records, key=lambda r: (r.retention_class, r.path)),
    )


def build_evidence_retention_archive_policy_report(repo_root: str | Path) -> EvidenceRetentionArchivePolicyReport:
    root = Path(repo_root).resolve()
    source_33e = find_source_33e_status(root)
    report_retention = build_report_retention(root)
    archive_manifest = build_backup_payload_archive_manifest(root)
    cleanup_plan = build_non_destructive_cleanup_plan(root, report_retention)
    aging_ledger = build_evidence_aging_ledger(
        report_retention.records,
        archive_manifest.records,
        cleanup_plan.cleanup_records,
    )
    rules_complete = len(default_retention_rules()) >= 7
    safety = SafetySnapshot()
    ready = (
        source_33e.complete
        and rules_complete
        and report_retention.complete
        and archive_manifest.complete
        and cleanup_plan.complete
        and aging_ledger.complete
        and not safety.destructive_cleanup_performed
        and not safety.exchange_submit_performed
        and not safety.trading_action_performed
        and not safety.training_performed
        and not safety.reload_performed
        and not safety.runtime_overlay_activated
    )
    return EvidenceRetentionArchivePolicyReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        status="READY" if ready else "NOT_READY",
        decision=READY_DECISION if ready else NOT_READY_DECISION,
        generated_at_epoch_ms=_now_ms(),
        source_33e=source_33e,
        retention_rules_complete=rules_complete,
        report_retention=report_retention,
        backup_payload_archive_manifest=archive_manifest,
        non_destructive_cleanup_plan=cleanup_plan,
        evidence_aging_ledger=aging_ledger,
        safety_snapshot=safety,
        recommended_next_phase="Proceed to 33G only after 33F READY; no destructive cleanup authorized by this patch." if ready else "Fix source or ledger blockers before continuing.",
    )


def summarize_report(report: EvidenceRetentionArchivePolicyReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "check_name": "evidence_retention_archive_policy",
        "patch_id": report.patch_id,
        "patch_version": report.patch_version,
        "status": report.status,
        "decision": report.decision,
        "source_33e_complete": report.source_33e.complete,
        "source_33e_report": report.source_33e.report_path,
        "retention_rules_complete": report.retention_rules_complete,
        "report_retention_complete": report.report_retention.complete,
        "scanned_report_count": report.report_retention.scanned_report_count,
        "latest_ready_report_count": report.report_retention.latest_ready_report_count,
        "historical_ready_report_count": report.report_retention.historical_ready_report_count,
        "not_ready_report_count": report.report_retention.not_ready_report_count,
        "ledger_report_count": report.report_retention.ledger_report_count,
        "unknown_report_count": report.report_retention.unknown_report_count,
        "backup_payload_archive_manifest_complete": report.backup_payload_archive_manifest.complete,
        "backup_dir_count": report.backup_payload_archive_manifest.backup_dir_count,
        "payload_dir_count": report.backup_payload_archive_manifest.payload_dir_count,
        "legacy_patch_dir_count": report.backup_payload_archive_manifest.legacy_patch_dir_count,
        "archive_manifest_record_count": report.backup_payload_archive_manifest.manifest_record_count,
        "non_destructive_cleanup_plan_complete": report.non_destructive_cleanup_plan.complete,
        "cleanup_candidate_count": report.non_destructive_cleanup_plan.candidate_count,
        "pycache_candidate_count": report.non_destructive_cleanup_plan.pycache_candidate_count,
        "pytest_cache_candidate_count": report.non_destructive_cleanup_plan.pytest_cache_candidate_count,
        "duplicate_attempt_report_count": report.non_destructive_cleanup_plan.duplicate_attempt_report_count,
        "evidence_aging_ledger_complete": report.evidence_aging_ledger.complete,
        "aging_total_record_count": report.evidence_aging_ledger.total_record_count,
        "aging_hot_count": report.evidence_aging_ledger.hot_count,
        "aging_warm_count": report.evidence_aging_ledger.warm_count,
        "aging_cold_count": report.evidence_aging_ledger.cold_count,
        "archive_candidate_count": report.evidence_aging_ledger.archive_candidate_count,
        "approved_for_live_real": report.safety_snapshot.approved_for_live_real,
        "approved_for_paper_transition": report.safety_snapshot.approved_for_paper_transition,
        "approved_for_exchange_submit": report.safety_snapshot.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.safety_snapshot.approved_for_runtime_overlay,
        "live_real_submit_allowed": report.safety_snapshot.live_real_submit_allowed,
        "paper_submit_allowed": report.safety_snapshot.paper_submit_allowed,
        "network_submit_allowed": report.safety_snapshot.network_submit_allowed,
        "exchange_submit_allowed": report.safety_snapshot.exchange_submit_allowed,
        "runtime_overlay_allowed": report.safety_snapshot.runtime_overlay_allowed,
        "trading_action_performed": report.safety_snapshot.trading_action_performed,
        "training_performed": report.safety_snapshot.training_performed,
        "reload_performed": report.safety_snapshot.reload_performed,
        "exchange_submit_performed": report.safety_snapshot.exchange_submit_performed,
        "runtime_overlay_activated": report.safety_snapshot.runtime_overlay_activated,
        "destructive_cleanup_performed": report.safety_snapshot.destructive_cleanup_performed,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def write_evidence_retention_archive_policy_report(
    repo_root: str | Path,
    reports_dir: str | Path | None = None,
) -> tuple[EvidenceRetentionArchivePolicyReport, dict[str, str]]:
    root = Path(repo_root).resolve()
    report = build_evidence_retention_archive_policy_report(root)
    output_dir = Path(reports_dir).resolve() if reports_dir is not None else root / "reports" / "recovery"
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    suffix = "ready" if report.ok else "not_ready"
    main_path = output_dir / f"{PATCH_ID}_evidence_retention_archive_policy_{timestamp}_{suffix}.json"
    rules_path = output_dir / f"{PATCH_ID}_retention_rules_ledger_{timestamp}.json"
    archive_path = output_dir / f"{PATCH_ID}_backup_payload_archive_manifest_{timestamp}.json"
    cleanup_path = output_dir / f"{PATCH_ID}_non_destructive_cleanup_plan_{timestamp}.json"
    aging_path = output_dir / f"{PATCH_ID}_evidence_aging_ledger_{timestamp}.json"
    _write_json(main_path, report.to_dict())
    _write_json(rules_path, [asdict(rule) for rule in default_retention_rules()])
    _write_json(archive_path, asdict(report.backup_payload_archive_manifest))
    _write_json(cleanup_path, asdict(report.non_destructive_cleanup_plan))
    _write_json(aging_path, asdict(report.evidence_aging_ledger))
    return report, {
        "report_path": str(main_path),
        "retention_rules_ledger_path": str(rules_path),
        "backup_payload_archive_manifest_path": str(archive_path),
        "non_destructive_cleanup_plan_path": str(cleanup_path),
        "evidence_aging_ledger_path": str(aging_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    if args.reports_dir:
        report, paths = write_evidence_retention_archive_policy_report(args.repo_root, args.reports_dir)
        summary = summarize_report(report)
        summary.update(paths)
    else:
        report = build_evidence_retention_archive_policy_report(args.repo_root)
        summary = summarize_report(report)
    if args.once_json:
        print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
