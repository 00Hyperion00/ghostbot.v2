from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436633E"
PATCH_VERSION = "4B.4.3.6.6.33E"
PATCH_NAME = "Status Conflict Resolver"

READY_DECISION = "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE"
NOT_READY_DECISION = "STATUS_CONFLICT_RESOLVER_NOT_READY"

DECISIVE_STATUSES = {
    "ready",
    "not_ready",
    "approval_required",
    "execution_evidence_required",
    "operator_required",
    "authorization_required",
    "input_required",
    "unlock_required",
    "lock_required",
    "sqlite_required",
}

NON_DECISIVE_STATUSES = {
    "snapshot",
    "manifest",
    "quarantine_manifest",
    "request",
    "intent",
    "seed",
    "delta",
    "baseline",
    "metrics",
    "unknown",
    "malformed_json",
}

BLOCKING_STATUSES = {
    "not_ready",
    "approval_required",
    "execution_evidence_required",
    "operator_required",
    "authorization_required",
    "input_required",
    "unlock_required",
    "lock_required",
}

FILENAME_STATUS_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), status)
    for pattern, status in (
        (r"(?:^|[_\-])execution[_\-]evidence[_\-]required(?:[_\-.]|$)", "execution_evidence_required"),
        (r"(?:^|[_\-])approval[_\-]required(?:[_\-.]|$)", "approval_required"),
        (r"(?:^|[_\-])operator[_\-]required(?:[_\-.]|$)", "operator_required"),
        (r"(?:^|[_\-])authorization[_\-]required(?:[_\-.]|$)", "authorization_required"),
        (r"(?:^|[_\-])input[_\-]required(?:[_\-.]|$)", "input_required"),
        (r"(?:^|[_\-])unlock[_\-]required(?:[_\-.]|$)", "unlock_required"),
        (r"(?:^|[_\-])lock[_\-]required(?:[_\-.]|$)", "lock_required"),
        (r"(?:^|[_\-])sqlite[_\-]required(?:[_\-.]|$)", "sqlite_required"),
        (r"(?:^|[_\-])not[_\-]ready(?:[_\-.]|$)", "not_ready"),
        (r"(?:^|[_\-])ready(?:[_\-.]|$)", "ready"),
        (r"(?:^|[_\-])quarantine[_\-]manifest(?:[_\-.]|$)", "quarantine_manifest"),
        (r"(?:^|[_\-])evidence[_\-]pack[_\-]manifest(?:[_\-.]|$)", "manifest"),
        (r"(?:^|[_\-])manifest(?:[_\-.]|$)", "manifest"),
        (r"(?:^|[_\-])snapshot(?:[_\-.]|$)", "snapshot"),
        (r"(?:^|[_\-])request(?:[_\-.]|$)", "request"),
        (r"(?:^|[_\-])intent(?:[_\-.]|$)", "intent"),
        (r"(?:^|[_\-])seed(?:[_\-.]|$)", "seed"),
        (r"(?:^|[_\-])delta(?:[_\-.]|$)", "delta"),
        (r"(?:^|[_\-])baseline(?:[_\-.]|$)", "baseline"),
        (r"(?:^|[_\-])metrics(?:[_\-.]|$)", "metrics"),
    )
)

TIMESTAMP_RE = re.compile(r"20\d{6}T\d{6}Z|20\d{6}_\d{6}Z?|20\d{12}", re.IGNORECASE)
PHASE_RE = re.compile(r"4B4366[0-9A-Z_\-]+", re.IGNORECASE)
SOURCE_33D_PATTERN = "4B436633D_runtime_safety_lockdown_*_ready.json"


@dataclass(frozen=True)
class StatusSignal:
    status: str
    source: str
    confidence: str
    raw_value: Any = None


@dataclass(frozen=True)
class EvidenceRecord:
    path: str
    sha256: str | None
    phase_token: str | None
    timestamp_token: str | None
    filename_status: str
    filename_status_source: str
    payload_status: str
    payload_status_source: str
    resolved_status: str
    resolution_rule: str
    conflict: bool
    classification: str
    parse_error: str | None
    triage_action: str


@dataclass(frozen=True)
class StatusConflictSummary:
    complete: bool
    conflict_count: int
    resolved_conflict_count: int
    unresolved_conflict_count: int
    records: list[EvidenceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class UnknownEvidenceSummary:
    complete: bool
    unknown_count: int
    classified_unknown_count: int
    residual_unknown_count: int
    classification_counts: dict[str, int] = field(default_factory=dict)
    records: list[EvidenceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class MalformedJsonSummary:
    complete: bool
    malformed_count: int
    bom_count: int
    non_object_root_count: int
    json_decode_count: int
    other_error_count: int
    records: list[EvidenceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class SourceGate:
    complete: bool
    source_33d_report: str | None
    source_33d_status: str | None
    source_33d_decision: str | None
    source_33d_runtime_safety_lockdown_complete: bool
    source_33d_unguarded_destructive_endpoint_count: int | None


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class StatusConflictResolverReport:
    patch_id: str
    patch_version: str
    patch_name: str
    check_name: str
    status: str
    decision: str
    ok: bool
    generated_at_epoch_ms: int
    reports_root: str
    total_json_file_count: int
    source_gate: SourceGate
    status_conflict_summary: StatusConflictSummary
    unknown_evidence_summary: UnknownEvidenceSummary
    malformed_json_summary: MalformedJsonSummary
    safety_snapshot: SafetySnapshot
    recommended_next_phase: str


def _now_ms() -> int:
    return int(time.time() * 1000)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _phase_token_from_name(name: str) -> str | None:
    match = PHASE_RE.search(name)
    if not match:
        return None
    token = match.group(0).upper().rstrip("_-.")
    token = re.sub(r"_(?:READY|NOT_READY|APPROVAL_REQUIRED|EXECUTION_EVIDENCE_REQUIRED|OPERATOR_REQUIRED|AUTHORIZATION_REQUIRED|INPUT_REQUIRED|UNLOCK_REQUIRED|LOCK_REQUIRED|SQLITE_REQUIRED)$", "", token)
    return token


def _timestamp_token_from_name(name: str) -> str | None:
    match = TIMESTAMP_RE.search(name)
    return match.group(0) if match else None


def _filename_status(path: Path) -> StatusSignal:
    name = path.name
    for pattern, status in FILENAME_STATUS_PATTERNS:
        if pattern.search(name):
            return StatusSignal(status=status, source="filename_token", confidence="high", raw_value=name)
    return StatusSignal(status="unknown", source="filename_unclassified", confidence="low", raw_value=name)


def _normalize_status_value(value: Any) -> str | None:
    if isinstance(value, bool):
        return "ready" if value else "not_ready"
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    text = text.replace("-", "_").replace(" ", "_")
    if "execution_evidence_required" in text:
        return "execution_evidence_required"
    if "approval_required" in text:
        return "approval_required"
    if "operator_required" in text:
        return "operator_required"
    if "authorization_required" in text or "authorisation_required" in text:
        return "authorization_required"
    if "input_required" in text:
        return "input_required"
    if "unlock_required" in text:
        return "unlock_required"
    if "lock_required" in text:
        return "lock_required"
    if "sqlite_required" in text:
        return "sqlite_required"
    if text in {"ready", "ok", "pass", "passed", "accepted", "complete", "completed", "success", "true"}:
        return "ready"
    if text in {"not_ready", "fail", "failed", "blocked", "incomplete", "false"}:
        return "not_ready"
    if "not_ready" in text:
        return "not_ready"
    if text.endswith("_ready") or "ready_no" in text or "ready_all" in text or "_ready_" in text:
        return "ready"
    return None


def _payload_status(obj: Mapping[str, Any]) -> StatusSignal:
    priority_keys = (
        "status",
        "decision",
        "baseline_status",
        "gate_status",
        "result",
        "runtime_safety_lockdown_complete",
        "phase_hygiene_complete",
        "canonical_evidence_complete",
        "ok",
        "ready",
        "accepted",
        "approved",
        "complete",
    )
    for key in priority_keys:
        if key not in obj:
            continue
        normalized = _normalize_status_value(obj.get(key))
        if normalized:
            return StatusSignal(status=normalized, source=f"payload:{key}", confidence="high", raw_value=obj.get(key))

    for key in ("summary", "result", "gate", "decision_summary"):
        nested = obj.get(key)
        if isinstance(nested, Mapping):
            nested_status = _payload_status(nested)
            if nested_status.status != "unknown":
                return StatusSignal(
                    status=nested_status.status,
                    source=f"payload:{key}.{nested_status.source}",
                    confidence="medium",
                    raw_value=nested_status.raw_value,
                )

    return StatusSignal(status="unknown", source="payload_unclassified", confidence="low", raw_value=None)


def _classify_unknown(path: Path, payload: Mapping[str, Any] | None) -> tuple[str, str]:
    text = path.as_posix().lower()
    if payload is not None:
        payload_keys = " ".join(str(key).lower() for key in payload.keys())
        text = f"{text} {payload_keys}"
    if any(token in text for token in ("snapshot", "dump", "scan_dump")):
        return "snapshot", "retain_snapshot_non_decisive"
    if any(token in text for token in ("manifest", "ledger")):
        return "ledger_or_manifest", "retain_ledger_non_decisive"
    if any(token in text for token in ("request", "intent", "candidate")):
        return "operator_request_or_intent", "retain_request_non_decisive"
    if any(token in text for token in ("delta", "continuity", "baseline", "metrics", "seed")):
        return "research_delta_or_metrics", "retain_research_non_decisive"
    if any(token in text for token in ("near_miss", "shadow", "hyp005", "hyp006", "observation")):
        return "shadow_research_evidence", "retain_shadow_non_decisive"
    if any(token in text for token in ("config", "settings", "preflight")):
        return "configuration_or_preflight_evidence", "retain_config_non_decisive"
    return "residual_unknown", "manual_review_non_blocking"


def _classify_malformed_error(parse_error: str) -> str:
    lowered = parse_error.lower()
    if "utf-8 bom" in lowered or "utf-8-sig" in lowered:
        return "malformed_bom"
    if "root is not an object" in lowered:
        return "malformed_non_object_root"
    if "jsondecodeerror" in lowered:
        return "malformed_json_decode"
    return "malformed_other"


def _resolve_status(filename: StatusSignal, payload: StatusSignal, path: Path, payload_obj: Mapping[str, Any] | None) -> tuple[str, str, bool, str, str]:
    filename_status = filename.status
    payload_status = payload.status

    if filename_status == "malformed_json" or payload_status == "malformed_json":
        return "malformed_json", "malformed_json_triage", False, "malformed_json", "manual_parse_repair_or_reclassify"

    filename_decisive = filename_status in DECISIVE_STATUSES
    payload_decisive = payload_status in DECISIVE_STATUSES
    conflict = filename_decisive and payload_decisive and filename_status != payload_status

    if conflict:
        if filename_status in BLOCKING_STATUSES:
            return filename_status, "filename_blocking_status_precedence", True, "status_conflict_resolved", "retain_with_filename_precedence"
        if payload_status in BLOCKING_STATUSES:
            return payload_status, "payload_blocking_status_precedence", True, "status_conflict_resolved", "retain_with_payload_precedence"
        return filename_status, "filename_status_precedence", True, "status_conflict_resolved", "retain_with_filename_precedence"

    if filename_decisive:
        return filename_status, "filename_decisive_status", False, "decisive_evidence", "retain"
    if payload_decisive:
        return payload_status, "payload_decisive_status", False, "decisive_evidence", "retain"
    if filename_status in NON_DECISIVE_STATUSES and filename_status != "unknown":
        return filename_status, "filename_non_decisive_classification", False, "non_decisive_evidence", "retain_non_decisive"
    if payload_status in NON_DECISIVE_STATUSES and payload_status != "unknown":
        return payload_status, "payload_non_decisive_classification", False, "non_decisive_evidence", "retain_non_decisive"

    classification, action = _classify_unknown(path, payload_obj)
    return "unknown", "unknown_classifier", False, classification, action


def _load_json(path: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, Mapping):
        return None, "JSON root is not an object"
    return data, None


def iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    ignored_parts = {"__pycache__", ".pytest_cache", "_patch_backup", "_patch_payload", "legacy_patches"}
    result: list[Path] = []
    for path in root.rglob("*.json"):
        parts = set(path.parts)
        if any(part in parts for part in ignored_parts):
            continue
        if any(part.startswith("_patch_backup") or part.startswith("_patch_payload") for part in path.parts):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.as_posix().lower())


def analyze_evidence_file(path: Path, project_root: Path) -> EvidenceRecord:
    rel = _to_rel(path, project_root)
    try:
        sha = _sha256_file(path)
    except OSError:
        sha = None
    filename_signal = _filename_status(path)
    payload_obj, parse_error = _load_json(path)
    if parse_error is not None:
        malformed_class = _classify_malformed_error(parse_error)
        return EvidenceRecord(
            path=rel,
            sha256=sha,
            phase_token=_phase_token_from_name(path.name),
            timestamp_token=_timestamp_token_from_name(path.name),
            filename_status=filename_signal.status,
            filename_status_source=filename_signal.source,
            payload_status="malformed_json",
            payload_status_source="json_parse_error",
            resolved_status="malformed_json",
            resolution_rule="malformed_json_triage",
            conflict=False,
            classification=malformed_class,
            parse_error=parse_error,
            triage_action="manual_parse_repair_or_archive_as_raw_observation",
        )
    payload_signal = _payload_status(payload_obj or {})
    resolved, rule, conflict, classification, action = _resolve_status(filename_signal, payload_signal, path, payload_obj)
    return EvidenceRecord(
        path=rel,
        sha256=sha,
        phase_token=_phase_token_from_name(path.name),
        timestamp_token=_timestamp_token_from_name(path.name),
        filename_status=filename_signal.status,
        filename_status_source=filename_signal.source,
        payload_status=payload_signal.status,
        payload_status_source=payload_signal.source,
        resolved_status=resolved,
        resolution_rule=rule,
        conflict=conflict,
        classification=classification,
        parse_error=None,
        triage_action=action,
    )



def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ready", "complete", "passed"}
    return bool(value)


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            return int(stripped)
    return None


def _mapping_get(mapping: Mapping[str, Any], key: str) -> Any:
    return mapping.get(key) if isinstance(mapping, Mapping) else None


def _nested_mapping(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = _mapping_get(mapping, key)
    return value if isinstance(value, Mapping) else {}


def _resolve_33d_unguarded_count(payload: Mapping[str, Any]) -> int | None:
    direct = _coerce_int(payload.get("unguarded_destructive_endpoint_count"))
    if direct is not None:
        return direct
    audit = _nested_mapping(payload, "destructive_endpoint_audit")
    nested = _coerce_int(audit.get("unguarded_destructive_endpoint_count"))
    if nested is not None:
        return nested
    unguarded = payload.get("unguarded_destructive_endpoints")
    if isinstance(unguarded, list):
        return len(unguarded)
    nested_unguarded = audit.get("unguarded_destructive_endpoints")
    if isinstance(nested_unguarded, list):
        return len(nested_unguarded)
    if _coerce_bool(audit.get("complete")):
        return 0
    return None


def _resolve_33d_destructive_audit_complete(payload: Mapping[str, Any]) -> bool:
    direct = payload.get("destructive_endpoint_audit_complete")
    if direct is not None:
        return _coerce_bool(direct)
    audit = _nested_mapping(payload, "destructive_endpoint_audit")
    nested = audit.get("complete")
    if nested is not None:
        return _coerce_bool(nested)
    unguarded = _resolve_33d_unguarded_count(payload)
    return unguarded == 0


def _resolve_33d_runtime_complete(payload: Mapping[str, Any]) -> bool:
    direct = payload.get("runtime_safety_lockdown_complete")
    if direct is not None:
        return _coerce_bool(direct)
    nested = _nested_mapping(payload, "runtime_safety_lockdown")
    nested_complete = nested.get("complete")
    if nested_complete is not None:
        return _coerce_bool(nested_complete)
    return (
        _coerce_bool(payload.get("central_submit_guard_passed", True))
        and _coerce_bool(payload.get("operator_action_guard_passed", True))
        and _coerce_bool(payload.get("runtime_overlay_guard_passed", True))
        and _resolve_33d_destructive_audit_complete(payload)
        and _resolve_33d_unguarded_count(payload) == 0
    )


def _resolve_33d_fail_closed_safety(payload: Mapping[str, Any]) -> bool:
    false_fields = (
        "approved_for_live_real",
        "approved_for_paper_transition",
        "approved_for_exchange_submit",
        "approved_for_runtime_overlay",
        "live_real_submit_allowed",
        "paper_submit_allowed",
        "network_submit_allowed",
        "exchange_submit_allowed",
        "runtime_overlay_allowed",
        "trading_action_performed",
        "training_performed",
        "reload_performed",
        "exchange_submit_performed",
        "runtime_overlay_activated",
        "destructive_cleanup_performed",
    )
    return all(not _coerce_bool(payload.get(field, False)) for field in false_fields)


def _source_33d_is_ready(payload: Mapping[str, Any], candidate: Path) -> tuple[bool, bool, int | None]:
    status = str(payload.get("status", "")).upper()
    decision = str(payload.get("decision", ""))
    filename_ready = candidate.name.lower().endswith("_ready.json")
    status_ready = status == "READY" or filename_ready
    decision_ready = (not decision) or decision.startswith("RUNTIME_SAFETY_LOCKDOWN_READY")
    unguarded = _resolve_33d_unguarded_count(payload)
    runtime_complete = _resolve_33d_runtime_complete(payload)
    fail_closed = _resolve_33d_fail_closed_safety(payload)
    complete = bool(status_ready and decision_ready and runtime_complete and unguarded == 0 and fail_closed)
    return complete, runtime_complete, unguarded


def _find_source_33d(project_root: Path) -> SourceGate:
    candidates = sorted(
        project_root.glob(f"reports/recovery/{SOURCE_33D_PATTERN}"),
        key=lambda item: item.stat().st_mtime if item.exists() else 0,
        reverse=True,
    )
    latest_payload: Mapping[str, Any] = {}
    latest_path: Path | None = None
    for candidate in candidates:
        payload, parse_error = _load_json(candidate)
        if parse_error or not isinstance(payload, Mapping):
            continue
        latest_payload = payload
        latest_path = candidate
        complete, runtime_complete, unguarded = _source_33d_is_ready(payload, candidate)
        status = str(payload.get("status", "READY" if candidate.name.lower().endswith("_ready.json") else "UNKNOWN")).upper()
        decision = str(payload.get("decision", ""))
        if complete:
            return SourceGate(True, _to_rel(candidate, project_root), status, decision, runtime_complete, unguarded)
    if latest_path is None:
        return SourceGate(False, None, None, None, False, None)
    _, runtime_complete, unguarded = _source_33d_is_ready(latest_payload, latest_path)
    return SourceGate(
        False,
        _to_rel(latest_path, project_root),
        str(latest_payload.get("status", "READY" if latest_path.name.lower().endswith("_ready.json") else "UNKNOWN")).upper(),
        str(latest_payload.get("decision", "")),
        runtime_complete,
        unguarded,
    )

def build_status_conflict_resolver_report(project_root: Path | str = ".", reports_root: Path | str = "reports") -> StatusConflictResolverReport:
    root = Path(project_root).resolve()
    reports = (root / reports_root).resolve() if not Path(reports_root).is_absolute() else Path(reports_root).resolve()
    files = iter_json_files(reports)
    records = [analyze_evidence_file(path, root) for path in files]

    conflict_records = [record for record in records if record.conflict]
    resolved_conflicts = [record for record in conflict_records if "precedence" in record.resolution_rule]
    unresolved_conflicts = [record for record in conflict_records if record not in resolved_conflicts]

    unknown_records = [record for record in records if record.resolved_status == "unknown"]
    classified_unknown = [record for record in unknown_records if record.classification != "residual_unknown"]
    residual_unknown = [record for record in unknown_records if record.classification == "residual_unknown"]
    classification_counts: dict[str, int] = {}
    for record in unknown_records:
        classification_counts[record.classification] = classification_counts.get(record.classification, 0) + 1

    malformed_records = [record for record in records if record.resolved_status == "malformed_json"]
    malformed_classes = {"malformed_bom": 0, "malformed_non_object_root": 0, "malformed_json_decode": 0, "malformed_other": 0}
    for record in malformed_records:
        malformed_classes[record.classification] = malformed_classes.get(record.classification, 0) + 1

    source_gate = _find_source_33d(root)
    status_conflict_summary = StatusConflictSummary(
        complete=len(unresolved_conflicts) == 0,
        conflict_count=len(conflict_records),
        resolved_conflict_count=len(resolved_conflicts),
        unresolved_conflict_count=len(unresolved_conflicts),
        records=conflict_records[:500],
    )
    unknown_summary = UnknownEvidenceSummary(
        complete=True,
        unknown_count=len(unknown_records),
        classified_unknown_count=len(classified_unknown),
        residual_unknown_count=len(residual_unknown),
        classification_counts=dict(sorted(classification_counts.items())),
        records=unknown_records[:500],
    )
    malformed_summary = MalformedJsonSummary(
        complete=True,
        malformed_count=len(malformed_records),
        bom_count=malformed_classes.get("malformed_bom", 0),
        non_object_root_count=malformed_classes.get("malformed_non_object_root", 0),
        json_decode_count=malformed_classes.get("malformed_json_decode", 0),
        other_error_count=malformed_classes.get("malformed_other", 0),
        records=malformed_records[:500],
    )

    complete = source_gate.complete and status_conflict_summary.complete and unknown_summary.complete and malformed_summary.complete
    return StatusConflictResolverReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        check_name="status_conflict_resolver",
        status="READY" if complete else "NOT_READY",
        decision=READY_DECISION if complete else NOT_READY_DECISION,
        ok=True,
        generated_at_epoch_ms=_now_ms(),
        reports_root=_to_rel(reports, root),
        total_json_file_count=len(files),
        source_gate=source_gate,
        status_conflict_summary=status_conflict_summary,
        unknown_evidence_summary=unknown_summary,
        malformed_json_summary=malformed_summary,
        safety_snapshot=SafetySnapshot(),
        recommended_next_phase="Proceed to 33F evidence retention and archive policy" if complete else "Fix unresolved status conflicts or missing 33D READY source before continuing",
    )


def check_status_conflict_resolver(project_root: Path | str = ".", reports_root: Path | str = "reports") -> dict[str, Any]:
    report = build_status_conflict_resolver_report(project_root=project_root, reports_root=reports_root)
    return {
        "ok": True,
        "check_name": report.check_name,
        "patch_id": report.patch_id,
        "patch_version": report.patch_version,
        "status": report.status,
        "decision": report.decision,
        "source_33d_complete": report.source_gate.complete,
        "source_33d_report": report.source_gate.source_33d_report,
        "status_conflict_resolution_complete": report.status_conflict_summary.complete,
        "status_conflict_count": report.status_conflict_summary.conflict_count,
        "resolved_conflict_count": report.status_conflict_summary.resolved_conflict_count,
        "unresolved_conflict_count": report.status_conflict_summary.unresolved_conflict_count,
        "unknown_evidence_triage_complete": report.unknown_evidence_summary.complete,
        "unknown_count": report.unknown_evidence_summary.unknown_count,
        "classified_unknown_count": report.unknown_evidence_summary.classified_unknown_count,
        "residual_unknown_count": report.unknown_evidence_summary.residual_unknown_count,
        "malformed_json_triage_complete": report.malformed_json_summary.complete,
        "malformed_count": report.malformed_json_summary.malformed_count,
        "malformed_bom_count": report.malformed_json_summary.bom_count,
        "malformed_non_object_root_count": report.malformed_json_summary.non_object_root_count,
        "malformed_json_decode_count": report.malformed_json_summary.json_decode_count,
        "malformed_other_error_count": report.malformed_json_summary.other_error_count,
        "total_json_file_count": report.total_json_file_count,
        **asdict(report.safety_snapshot),
    }


def run_status_conflict_resolver(project_root: Path | str = ".", reports_root: Path | str = "reports", output_dir: Path | str = "reports/recovery") -> dict[str, Any]:
    root = Path(project_root).resolve()
    out_dir = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_status_conflict_resolver_report(project_root=root, reports_root=reports_root)
    suffix = "ready" if report.status == "READY" else "not_ready"
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    report_path = out_dir / f"{PATCH_ID}_status_conflict_resolver_{timestamp}_{suffix}.json"
    conflict_path = out_dir / f"{PATCH_ID}_status_conflict_resolution_ledger_{timestamp}.json"
    unknown_path = out_dir / f"{PATCH_ID}_unknown_evidence_classifier_ledger_{timestamp}.json"
    malformed_path = out_dir / f"{PATCH_ID}_malformed_json_triage_ledger_{timestamp}.json"

    report_path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    conflict_path.write_text(json.dumps(asdict(report.status_conflict_summary), indent=2, sort_keys=True), encoding="utf-8")
    unknown_path.write_text(json.dumps(asdict(report.unknown_evidence_summary), indent=2, sort_keys=True), encoding="utf-8")
    malformed_path.write_text(json.dumps(asdict(report.malformed_json_summary), indent=2, sort_keys=True), encoding="utf-8")

    summary = check_status_conflict_resolver(project_root=root, reports_root=reports_root)
    summary.update(
        {
            "report_path": str(report_path),
            "status_conflict_resolution_ledger_path": str(conflict_path),
            "unknown_evidence_classifier_ledger_path": str(unknown_path),
            "malformed_json_triage_ledger_path": str(malformed_path),
        }
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    payload = check_status_conflict_resolver(args.project_root, args.reports_root) if args.check_only else run_status_conflict_resolver(args.project_root, args.reports_root, args.reports_dir)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
