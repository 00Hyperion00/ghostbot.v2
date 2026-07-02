from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

PATCH_ID = "4B436633G"
PATCH_VERSION = "4B.4.3.6.6.33G"
PATCH_NAME = "Archive Execution Preflight"
READY_DECISION = "ARCHIVE_EXECUTION_PREFLIGHT_READY_DRY_RUN_VALIDATED"
NOT_READY_DECISION = "ARCHIVE_EXECUTION_PREFLIGHT_NOT_READY"

ARCHIVE_EXECUTION_ALLOWED = False
ARCHIVE_MOVE_PERFORMED = False
FILE_DELETE_PERFORMED = False
DESTRUCTIVE_CLEANUP_PERFORMED = False
TRADING_ACTION_PERFORMED = False
TRAINING_PERFORMED = False
RELOAD_PERFORMED = False
EXCHANGE_SUBMIT_PERFORMED = False
RUNTIME_OVERLAY_ACTIVATED = False

SOURCE_33F_PATTERN = "4B436633F_evidence_retention_archive_policy_*_ready.json"
OPTIONAL_OPERATOR_APPROVAL_FILE = "reports/recovery/4B436633G_operator_archive_plan_approval.json"


def _now_ts() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _epoch_ms() -> int:
    return int(time.time() * 1000)


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
        payload = json.loads(raw)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "json_root_is_not_object"
    return payload, None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _latest_by_mtime(paths: Iterable[Path]) -> Path | None:
    existing = [p for p in paths if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: (p.stat().st_mtime_ns, p.as_posix()))


def _truthy_complete(value: Any) -> bool:
    return value is True or str(value).strip().upper() in {"READY", "TRUE", "COMPLETE", "OK"}


def _nested_bool(payload: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if _truthy_complete(payload.get(key)):
            return True
    for value in payload.values():
        if isinstance(value, dict):
            for key in keys:
                if _truthy_complete(value.get(key)):
                    return True
    return False


def _find_source_33f_report(repo_root: Path) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    reports_dir = repo_root / "reports" / "recovery"
    latest = _latest_by_mtime(reports_dir.glob(SOURCE_33F_PATTERN))
    if latest is None:
        return None, None, "source_33f_ready_report_not_found"
    payload, error = _read_json(latest)
    if error is not None:
        return latest, None, error
    return latest, payload, None


def _source_33f_complete(payload: dict[str, Any] | None) -> bool:
    """Return True for both 33F check-summary and full run-report schemas.

    33F writes a compact summary with top-level `*_complete` flags and a full
    report with nested dataclass sections such as `source_33e.complete`,
    `report_retention.complete`, `backup_payload_archive_manifest.complete`,
    `non_destructive_cleanup_plan.complete`, and `evidence_aging_ledger.complete`.
    33G must accept either schema, but must still fail closed on destructive flags.
    """
    if not payload:
        return False

    def section_complete(summary_key: str, section_key: str) -> bool:
        if _truthy_complete(payload.get(summary_key)):
            return True
        section = payload.get(section_key)
        if isinstance(section, dict) and _truthy_complete(section.get("complete")):
            return True
        return False

    def safety_false(key: str) -> bool:
        if payload.get(key) is True:
            return False
        safety = payload.get("safety_snapshot")
        if isinstance(safety, dict) and safety.get(key) is True:
            return False
        return True

    status_ok = str(payload.get("status", "")).upper() == "READY"
    decision_text = str(payload.get("decision", "")).upper()
    decision_ok = "EVIDENCE_RETENTION_ARCHIVE_POLICY_READY" in decision_text or (
        "READY" in decision_text and "NOT_READY" not in decision_text
    )

    source_33e_ok = section_complete("source_33e_complete", "source_33e")
    required_sections_ok = all(
        [
            section_complete("retention_rules_complete", "retention_rules"),
            section_complete("report_retention_complete", "report_retention"),
            section_complete("backup_payload_archive_manifest_complete", "backup_payload_archive_manifest"),
            section_complete("non_destructive_cleanup_plan_complete", "non_destructive_cleanup_plan"),
            section_complete("evidence_aging_ledger_complete", "evidence_aging_ledger"),
        ]
    )
    no_destructive = all(
        safety_false(key)
        for key in (
            "destructive_cleanup_performed",
            "archive_move_performed",
            "file_delete_performed",
            "exchange_submit_performed",
            "trading_action_performed",
            "training_performed",
            "reload_performed",
            "runtime_overlay_activated",
        )
    )
    disallowed_execution_flags_closed = all(
        payload.get(key) is not True
        for key in (
            "archive_execution_allowed",
            "approved_for_live_real",
            "approved_for_paper_transition",
            "approved_for_exchange_submit",
            "approved_for_runtime_overlay",
            "network_submit_allowed",
            "exchange_submit_allowed",
            "paper_submit_allowed",
            "live_real_submit_allowed",
            "runtime_overlay_allowed",
        )
    )
    return status_ok and decision_ok and source_33e_ok and required_sections_ok and no_destructive and disallowed_execution_flags_closed

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _dir_digest(path: Path, repo_root: Path) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    total_bytes = 0
    file_count = 0
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = _rel(file_path, repo_root)
        data_hash = _sha256_file(file_path)
        size = file_path.stat().st_size
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(data_hash.encode("ascii"))
        digest.update(b"\n")
        total_bytes += size
        file_count += 1
    return digest.hexdigest(), total_bytes, file_count


def _archive_target_for(source_rel: str) -> str:
    normalized = source_rel.replace("\\", "/")
    if normalized.startswith("tools/_patch_backup_"):
        return "archive/patch_backups/" + normalized.removeprefix("tools/")
    if normalized.startswith("tools/_patch_payload_"):
        return "archive/patch_payloads/" + normalized.removeprefix("tools/")
    if normalized.startswith("legacy_patches/"):
        return "archive/legacy_patches/" + normalized.removeprefix("legacy_patches/")
    return "archive/misc/" + normalized


def _candidate_paths(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    tools_dir = repo_root / "tools"
    if tools_dir.exists():
        candidates.extend(sorted(p for p in tools_dir.glob("_patch_backup_*") if p.is_dir()))
        candidates.extend(sorted(p for p in tools_dir.glob("_patch_payload_*") if p.is_dir()))
    legacy_dir = repo_root / "legacy_patches"
    if legacy_dir.exists():
        candidates.extend(sorted(p for p in legacy_dir.iterdir()))
    # Preserve deterministic order and avoid duplicates.
    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = path.resolve().as_posix()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


@dataclass(frozen=True)
class SourceGate:
    complete: bool
    source_33f_report: str | None
    source_33f_error: str | None
    status: str | None
    decision: str | None


@dataclass(frozen=True)
class OperatorApprovedArchivePlanValidator:
    complete: bool
    operator_approval_file: str
    operator_approval_present: bool
    operator_approval_valid: bool
    operator_approval_status: str
    archive_execution_allowed: bool
    validation_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DryRunArchiveMovePreviewRecord:
    source_path: str
    target_path: str
    source_exists: bool
    source_type: str
    file_count: int
    size_bytes: int
    source_sha256: str | None
    action: str
    would_move: bool


@dataclass(frozen=True)
class DryRunArchiveMovePreview:
    complete: bool
    record_count: int
    total_file_count: int
    total_size_bytes: int
    preview_records: list[DryRunArchiveMovePreviewRecord]


@dataclass(frozen=True)
class ManifestHashVerification:
    complete: bool
    manifest_sha256: str
    hashed_record_count: int
    missing_source_count: int
    verification_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RollbackPlanRecord:
    rollback_action: str
    from_path: str
    to_path: str
    precondition: str


@dataclass(frozen=True)
class RollbackPlan:
    complete: bool
    rollback_record_count: int
    records: list[RollbackPlanRecord]


@dataclass(frozen=True)
class ArchiveExecutionPreflightReport:
    patch_id: str
    patch_version: str
    patch_name: str
    check_name: str
    generated_at_epoch_ms: int
    status: str
    decision: str
    ok: bool
    source_gate: SourceGate
    operator_approved_archive_plan_validator: OperatorApprovedArchivePlanValidator
    dry_run_archive_move_preview: DryRunArchiveMovePreview
    manifest_hash_verification: ManifestHashVerification
    rollback_plan: RollbackPlan
    source_33f_complete: bool
    source_33f_report: str | None
    operator_approved_archive_plan_validator_complete: bool
    dry_run_archive_move_preview_complete: bool
    manifest_hash_verification_complete: bool
    rollback_plan_complete: bool
    archive_execution_preflight_complete: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    destructive_cleanup_performed: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    exchange_submit_performed: bool
    runtime_overlay_activated: bool
    network_submit_allowed: bool
    exchange_submit_allowed: bool
    paper_submit_allowed: bool
    live_real_submit_allowed: bool
    runtime_overlay_allowed: bool


def build_operator_approved_archive_plan_validator(repo_root: Path) -> OperatorApprovedArchivePlanValidator:
    approval_path = repo_root / OPTIONAL_OPERATOR_APPROVAL_FILE
    if not approval_path.exists():
        return OperatorApprovedArchivePlanValidator(
            complete=True,
            operator_approval_file=OPTIONAL_OPERATOR_APPROVAL_FILE,
            operator_approval_present=False,
            operator_approval_valid=True,
            operator_approval_status="APPROVAL_NOT_PRESENT_DRY_RUN_ONLY",
            archive_execution_allowed=False,
            validation_errors=[],
        )
    payload, error = _read_json(approval_path)
    errors: list[str] = []
    if error is not None or payload is None:
        errors.append(error or "approval_payload_missing")
        return OperatorApprovedArchivePlanValidator(
            complete=False,
            operator_approval_file=OPTIONAL_OPERATOR_APPROVAL_FILE,
            operator_approval_present=True,
            operator_approval_valid=False,
            operator_approval_status="INVALID_APPROVAL_FILE",
            archive_execution_allowed=False,
            validation_errors=errors,
        )

    # 33G never authorizes execution. A valid approval file may only approve dry-run review.
    requested_action = str(payload.get("requested_action", "dry_run_review")).lower()
    operator_approved = payload.get("operator_approved") is True
    dry_run_only = payload.get("dry_run_only") is not False
    valid = requested_action in {"dry_run_review", "preflight_only", "validate_only"} and dry_run_only
    if operator_approved and not valid:
        errors.append("operator_approval_attempts_archive_execution_or_non_dry_run_action")
        valid = False
    return OperatorApprovedArchivePlanValidator(
        complete=valid,
        operator_approval_file=OPTIONAL_OPERATOR_APPROVAL_FILE,
        operator_approval_present=True,
        operator_approval_valid=valid,
        operator_approval_status="VALID_DRY_RUN_APPROVAL" if valid else "INVALID_NON_DRY_RUN_APPROVAL",
        archive_execution_allowed=False,
        validation_errors=errors,
    )


def build_dry_run_archive_move_preview(repo_root: Path) -> DryRunArchiveMovePreview:
    records: list[DryRunArchiveMovePreviewRecord] = []
    total_size = 0
    total_files = 0
    for source in _candidate_paths(repo_root):
        source_rel = _rel(source, repo_root)
        if source.is_file():
            digest = _sha256_file(source)
            size = source.stat().st_size
            file_count = 1
            source_type = "file"
        elif source.is_dir():
            digest, size, file_count = _dir_digest(source, repo_root)
            source_type = "directory"
        else:
            digest = None
            size = 0
            file_count = 0
            source_type = "missing"
        total_size += size
        total_files += file_count
        records.append(
            DryRunArchiveMovePreviewRecord(
                source_path=source_rel,
                target_path=_archive_target_for(source_rel),
                source_exists=source.exists(),
                source_type=source_type,
                file_count=file_count,
                size_bytes=size,
                source_sha256=digest,
                action="dry_run_archive_move_preview_only",
                would_move=False,
            )
        )
    return DryRunArchiveMovePreview(
        complete=True,
        record_count=len(records),
        total_file_count=total_files,
        total_size_bytes=total_size,
        preview_records=records,
    )


def build_manifest_hash_verification(preview: DryRunArchiveMovePreview) -> ManifestHashVerification:
    errors: list[str] = []
    digest = hashlib.sha256()
    missing = 0
    for record in preview.preview_records:
        if not record.source_exists:
            missing += 1
            errors.append(f"missing_source:{record.source_path}")
        row = {
            "source_path": record.source_path,
            "target_path": record.target_path,
            "source_type": record.source_type,
            "file_count": record.file_count,
            "size_bytes": record.size_bytes,
            "source_sha256": record.source_sha256,
            "action": record.action,
        }
        digest.update(json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        digest.update(b"\n")
    return ManifestHashVerification(
        complete=missing == 0,
        manifest_sha256=digest.hexdigest(),
        hashed_record_count=preview.record_count,
        missing_source_count=missing,
        verification_errors=errors,
    )


def build_rollback_plan(preview: DryRunArchiveMovePreview) -> RollbackPlan:
    records = [
        RollbackPlanRecord(
            rollback_action="reverse_archive_move_if_future_execution_occurs",
            from_path=record.target_path,
            to_path=record.source_path,
            precondition="target_exists_and_source_missing_after_operator_approved_future_archive_execution",
        )
        for record in preview.preview_records
    ]
    return RollbackPlan(complete=True, rollback_record_count=len(records), records=records)


def build_archive_execution_preflight_report(repo_root: str | Path = ".") -> ArchiveExecutionPreflightReport:
    root = Path(repo_root).resolve()
    source_path, source_payload, source_error = _find_source_33f_report(root)
    source_complete = _source_33f_complete(source_payload)
    source_gate = SourceGate(
        complete=source_complete,
        source_33f_report=_rel(source_path, root) if source_path else None,
        source_33f_error=source_error,
        status=str(source_payload.get("status")) if source_payload else None,
        decision=str(source_payload.get("decision")) if source_payload else None,
    )
    operator_validator = build_operator_approved_archive_plan_validator(root)
    preview = build_dry_run_archive_move_preview(root)
    manifest = build_manifest_hash_verification(preview)
    rollback = build_rollback_plan(preview)

    preflight_complete = all(
        [
            source_gate.complete,
            operator_validator.complete,
            preview.complete,
            manifest.complete,
            rollback.complete,
        ]
    )
    status = "READY" if preflight_complete else "NOT_READY"
    decision = READY_DECISION if preflight_complete else NOT_READY_DECISION
    return ArchiveExecutionPreflightReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        check_name="archive_execution_preflight",
        generated_at_epoch_ms=_epoch_ms(),
        status=status,
        decision=decision,
        ok=preflight_complete,
        source_gate=source_gate,
        operator_approved_archive_plan_validator=operator_validator,
        dry_run_archive_move_preview=preview,
        manifest_hash_verification=manifest,
        rollback_plan=rollback,
        source_33f_complete=source_gate.complete,
        source_33f_report=source_gate.source_33f_report,
        operator_approved_archive_plan_validator_complete=operator_validator.complete,
        dry_run_archive_move_preview_complete=preview.complete,
        manifest_hash_verification_complete=manifest.complete,
        rollback_plan_complete=rollback.complete,
        archive_execution_preflight_complete=preflight_complete,
        archive_execution_allowed=ARCHIVE_EXECUTION_ALLOWED,
        archive_move_performed=ARCHIVE_MOVE_PERFORMED,
        file_delete_performed=FILE_DELETE_PERFORMED,
        destructive_cleanup_performed=DESTRUCTIVE_CLEANUP_PERFORMED,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        trading_action_performed=TRADING_ACTION_PERFORMED,
        training_performed=TRAINING_PERFORMED,
        reload_performed=RELOAD_PERFORMED,
        exchange_submit_performed=EXCHANGE_SUBMIT_PERFORMED,
        runtime_overlay_activated=RUNTIME_OVERLAY_ACTIVATED,
        network_submit_allowed=False,
        exchange_submit_allowed=False,
        paper_submit_allowed=False,
        live_real_submit_allowed=False,
        runtime_overlay_allowed=False,
    )


def summarize_report(report: ArchiveExecutionPreflightReport) -> dict[str, Any]:
    return {
        "check_name": report.check_name,
        "patch_id": report.patch_id,
        "patch_version": report.patch_version,
        "status": report.status,
        "decision": report.decision,
        "ok": report.ok,
        "source_33f_complete": report.source_33f_complete,
        "source_33f_report": report.source_33f_report,
        "operator_approved_archive_plan_validator_complete": report.operator_approved_archive_plan_validator_complete,
        "operator_approval_present": report.operator_approved_archive_plan_validator.operator_approval_present,
        "operator_approval_status": report.operator_approved_archive_plan_validator.operator_approval_status,
        "dry_run_archive_move_preview_complete": report.dry_run_archive_move_preview_complete,
        "dry_run_archive_move_record_count": report.dry_run_archive_move_preview.record_count,
        "dry_run_archive_total_file_count": report.dry_run_archive_move_preview.total_file_count,
        "dry_run_archive_total_size_bytes": report.dry_run_archive_move_preview.total_size_bytes,
        "manifest_hash_verification_complete": report.manifest_hash_verification_complete,
        "manifest_sha256": report.manifest_hash_verification.manifest_sha256,
        "manifest_missing_source_count": report.manifest_hash_verification.missing_source_count,
        "rollback_plan_complete": report.rollback_plan_complete,
        "rollback_record_count": report.rollback_plan.rollback_record_count,
        "archive_execution_preflight_complete": report.archive_execution_preflight_complete,
        "archive_execution_allowed": report.archive_execution_allowed,
        "archive_move_performed": report.archive_move_performed,
        "file_delete_performed": report.file_delete_performed,
        "destructive_cleanup_performed": report.destructive_cleanup_performed,
        "approved_for_live_real": report.approved_for_live_real,
        "approved_for_paper_transition": report.approved_for_paper_transition,
        "approved_for_exchange_submit": report.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.approved_for_runtime_overlay,
        "trading_action_performed": report.trading_action_performed,
        "training_performed": report.training_performed,
        "reload_performed": report.reload_performed,
        "exchange_submit_performed": report.exchange_submit_performed,
        "runtime_overlay_activated": report.runtime_overlay_activated,
        "network_submit_allowed": report.network_submit_allowed,
        "exchange_submit_allowed": report.exchange_submit_allowed,
        "paper_submit_allowed": report.paper_submit_allowed,
        "live_real_submit_allowed": report.live_real_submit_allowed,
        "runtime_overlay_allowed": report.runtime_overlay_allowed,
    }


def write_archive_execution_preflight_report(
    repo_root: str | Path = ".", reports_dir: str | Path | None = None
) -> tuple[ArchiveExecutionPreflightReport, dict[str, str]]:
    root = Path(repo_root).resolve()
    report = build_archive_execution_preflight_report(root)
    out_dir = Path(reports_dir).resolve() if reports_dir is not None else root / "reports" / "recovery"
    ts = _now_ts()
    suffix = "ready" if report.ok else "not_ready"

    report_path = out_dir / f"{PATCH_ID}_archive_execution_preflight_{ts}_{suffix}.json"
    operator_path = out_dir / f"{PATCH_ID}_operator_approved_archive_plan_validator_{ts}.json"
    preview_path = out_dir / f"{PATCH_ID}_dry_run_archive_move_preview_{ts}.json"
    manifest_path = out_dir / f"{PATCH_ID}_manifest_hash_verification_{ts}.json"
    rollback_path = out_dir / f"{PATCH_ID}_rollback_plan_{ts}.json"

    _write_json(report_path, asdict(report))
    _write_json(operator_path, asdict(report.operator_approved_archive_plan_validator))
    _write_json(preview_path, asdict(report.dry_run_archive_move_preview))
    _write_json(manifest_path, asdict(report.manifest_hash_verification))
    _write_json(rollback_path, asdict(report.rollback_plan))

    return report, {
        "report_path": str(report_path),
        "operator_approved_archive_plan_validator_path": str(operator_path),
        "dry_run_archive_move_preview_path": str(preview_path),
        "manifest_hash_verification_path": str(manifest_path),
        "rollback_plan_path": str(rollback_path),
    }
