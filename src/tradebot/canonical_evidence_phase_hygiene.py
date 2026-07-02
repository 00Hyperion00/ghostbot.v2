
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

PATCH_ID = "4B436633B"
PATCH_VERSION = "4B.4.3.6.6.33B"
PATCH_NAME = "Canonical Evidence & Phase Hygiene Cleanup"
READY_DECISION = "CANONICAL_EVIDENCE_PHASE_HYGIENE_READY_NO_TRADING_ACTIONS"
NOT_READY_DECISION = "CANONICAL_EVIDENCE_PHASE_HYGIENE_NOT_READY"

PHASE_PATTERN = re.compile(r"4B4366(?P<suffix>[0-9A-Z_\-]+)", re.IGNORECASE)
REPORT_STATUS_SUFFIX_PATTERN = re.compile(
    r"_(ready|not_ready|approval_required|execution_evidence_required)\.json$",
    re.IGNORECASE,
)
REPORT_TIMESTAMP_PATTERN = re.compile(r"20\d{6}T\d{6}Z")

CANONICAL_PHASE_ROOTS: tuple[str, ...] = (
    "tools",
    "tests",
    "docs",
)

NOISE_PATH_RULES: tuple[tuple[str, str], ...] = (
    ("__pycache__", "python bytecode cache"),
    (".pytest_cache", "pytest cache"),
    ("_patch_backup", "patch backup artifact"),
    ("_patch_payload", "patch payload staging artifact"),
    ("legacy_patches", "legacy patch archive"),
)

BAD_EVIDENCE_TOKENS: tuple[str, ...] = (
    "bad_evidence",
    "quarantine",
    "execution_evidence_required",
    "approval_required",
)

STATUS_PRIORITY: dict[str, int] = {
    "ready": 100,
    "not_ready": 90,
    "approval_required": 80,
    "execution_evidence_required": 70,
    "snapshot": 50,
    "manifest": 40,
    "unknown": 10,
    "malformed_json": 0,
}


@dataclass(slots=True)
class ClassifiedNoisePath:
    path: str
    category: str
    reason: str


@dataclass(slots=True)
class PhaseArtifactRecord:
    phase_key: str
    apply_files: list[str] = field(default_factory=list)
    check_files: list[str] = field(default_factory=list)
    run_files: list[str] = field(default_factory=list)
    rollback_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    doc_files: list[str] = field(default_factory=list)
    readme_apply_files: list[str] = field(default_factory=list)
    other_canonical_files: list[str] = field(default_factory=list)

    @property
    def artifact_count(self) -> int:
        return (
            len(self.apply_files)
            + len(self.check_files)
            + len(self.run_files)
            + len(self.rollback_files)
            + len(self.test_files)
            + len(self.doc_files)
            + len(self.readme_apply_files)
            + len(self.other_canonical_files)
        )

    @property
    def has_operational_artifact(self) -> bool:
        return bool(self.apply_files or self.check_files or self.run_files or self.doc_files or self.test_files)


@dataclass(slots=True)
class PhaseHygieneInventory:
    complete: bool
    phase_count: int
    latest_phase_key: str | None
    canonical_phase_artifact_count: int
    ignored_noise_count: int
    ignored_noise_sample: list[ClassifiedNoisePath]
    orphan_like_count: int
    orphan_like_sample: list[str]
    phases: list[PhaseArtifactRecord]


@dataclass(slots=True)
class ReportEvidenceRecord:
    path: str
    phase_key: str | None
    status: str
    status_source: str
    timestamp_token: str | None
    modified_epoch_ms: int
    sha256: str | None
    parse_error: str | None = None


@dataclass(slots=True)
class CanonicalEvidenceIndex:
    complete: bool
    reports_dir_exists: bool
    report_count: int
    classified_count: int
    ready_count: int
    not_ready_count: int
    approval_required_count: int
    execution_evidence_required_count: int
    snapshot_count: int
    manifest_count: int
    unknown_count: int
    malformed_json_count: int
    canonical_count: int
    canonical_records: list[ReportEvidenceRecord]


@dataclass(slots=True)
class BadEvidenceLedger:
    complete: bool
    bad_evidence_count: int
    malformed_json_count: int
    approval_required_count: int
    execution_evidence_required_count: int
    status_conflict_count: int
    records: list[dict[str, Any]]


@dataclass(slots=True)
class HygieneSafetySnapshot:
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    exchange_submit_performed: bool


@dataclass(slots=True)
class CanonicalEvidencePhaseHygieneReport:
    patch_id: str
    patch_version: str
    patch_name: str
    decision: str
    status: str
    generated_at_epoch_ms: int
    source_33a_report: str | None
    phase_hygiene_inventory: PhaseHygieneInventory
    canonical_evidence_index: CanonicalEvidenceIndex
    bad_evidence_ledger: BadEvidenceLedger
    safety_snapshot: HygieneSafetySnapshot
    recommended_next_phase: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# -----------------------------
# helpers
# -----------------------------

def now_epoch_ms() -> int:
    return int(time.time() * 1000)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_existing_files(root: Path, relative_roots: Iterable[str]) -> Iterable[Path]:
    for relative_root in relative_roots:
        base = root / relative_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                yield path


def classify_noise_path(relative_path: str) -> ClassifiedNoisePath | None:
    normalized = relative_path.replace("\\", "/")
    parts = normalized.split("/")
    lower = normalized.lower()
    for token, reason in NOISE_PATH_RULES:
        if token.lower() in (part.lower() for part in parts) or token.lower() in lower:
            return ClassifiedNoisePath(path=relative_path, category=token, reason=reason)
    if lower.endswith((".pyc", ".pyo")):
        return ClassifiedNoisePath(path=relative_path, category="bytecode", reason="compiled python artifact")
    return None


def extract_phase_key(relative_path: str) -> str | None:
    match = PHASE_PATTERN.search(relative_path.replace("-", "_"))
    if not match:
        return None
    suffix = match.group("suffix").upper().replace("-", "_")
    return "4B4366" + suffix.strip("_")


def extract_timestamp_token(path: str) -> str | None:
    match = REPORT_TIMESTAMP_PATTERN.search(path)
    return match.group(0) if match else None


def load_json_mapping(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # pragma: no cover - defensive fallback
            return None, f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root is not an object"
    return payload, None


def _normalized_status(value: Any) -> str | None:
    if isinstance(value, bool):
        return "ready" if value else "not_ready"
    if value is None:
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"ready", "pass", "passed", "ok", "true", "accepted"}:
        return "ready"
    if text in {"not_ready", "blocked", "fail", "failed", "false", "rejected"}:
        return "not_ready"
    if text in {"approval_required", "operator_approval_required"}:
        return "approval_required"
    if text in {"execution_evidence_required", "evidence_required"}:
        return "execution_evidence_required"
    if "approval_required" in text:
        return "approval_required"
    if "execution_evidence_required" in text:
        return "execution_evidence_required"
    if text.endswith("_ready") or "_ready_" in text:
        return "ready"
    if "not_ready" in text:
        return "not_ready"
    return None


def classify_report_status(relative_path: str, path: Path) -> tuple[str, str, str | None]:
    lowered = relative_path.lower()
    suffix_match = REPORT_STATUS_SUFFIX_PATTERN.search(lowered)
    suffix_status: str | None = None
    if suffix_match:
        suffix_status = suffix_match.group(1).lower()

    if lowered.endswith("_snapshot.json"):
        return "snapshot", "filename_suffix", None
    if lowered.endswith("_manifest.json") or "manifest" in lowered:
        return "manifest", "filename_token", None

    payload, parse_error = load_json_mapping(path)
    if parse_error is not None:
        return "malformed_json", "json_parse_error", parse_error

    payload_status: str | None = None
    for key in ("status", "decision", "baseline_status", "result", "gate_status"):
        if payload and key in payload:
            payload_status = _normalized_status(payload.get(key))
            if payload_status:
                break
    if payload_status is None and payload:
        for key in ("ready", "ok", "accepted", "approved"):
            if key in payload:
                payload_status = _normalized_status(payload.get(key))
                if payload_status:
                    break

    if suffix_status:
        if payload_status and payload_status != suffix_status:
            return suffix_status, f"filename_suffix_over_payload_{payload_status}", None
        return suffix_status, "filename_suffix", None
    if payload_status:
        return payload_status, "json_payload", None
    return "unknown", "unclassified", None


# -----------------------------
# inventory builders
# -----------------------------

def build_phase_hygiene_inventory(root: Path) -> PhaseHygieneInventory:
    records: dict[str, PhaseArtifactRecord] = {}
    ignored_noise: list[ClassifiedNoisePath] = []
    orphan_like: list[str] = []
    canonical_artifact_count = 0

    candidate_files = list(iter_existing_files(root, CANONICAL_PHASE_ROOTS))
    for path in candidate_files:
        relative = safe_relative(path, root)
        noise = classify_noise_path(relative)
        if noise is not None:
            ignored_noise.append(noise)
            continue

        phase_key = extract_phase_key(relative)
        if phase_key is None:
            name_lower = path.name.lower()
            if any(token in name_lower for token in ("apply_4b", "check_4b", "run_4b", "rollback_4b", "test_4b")):
                orphan_like.append(relative)
            continue

        canonical_artifact_count += 1
        record = records.setdefault(phase_key, PhaseArtifactRecord(phase_key=phase_key))
        name_lower = path.name.lower()
        if relative.startswith("tools/apply_"):
            record.apply_files.append(relative)
        elif relative.startswith("tools/check_"):
            record.check_files.append(relative)
        elif relative.startswith("tools/run_"):
            record.run_files.append(relative)
        elif relative.startswith("tools/rollback_"):
            record.rollback_files.append(relative)
        elif relative.startswith("tests/test_"):
            record.test_files.append(relative)
        elif relative.startswith("docs/"):
            record.doc_files.append(relative)
        elif name_lower.startswith("readme_apply_"):
            record.readme_apply_files.append(relative)
        else:
            record.other_canonical_files.append(relative)

    phases = sorted(records.values(), key=lambda item: item.phase_key)
    latest_phase_key = phases[-1].phase_key if phases else None
    severe_orphans = [item for item in orphan_like if "__pycache__" not in item and "_patch_" not in item]
    complete = bool(phases) and len(severe_orphans) == 0

    return PhaseHygieneInventory(
        complete=complete,
        phase_count=len(phases),
        latest_phase_key=latest_phase_key,
        canonical_phase_artifact_count=canonical_artifact_count,
        ignored_noise_count=len(ignored_noise),
        ignored_noise_sample=ignored_noise[:100],
        orphan_like_count=len(severe_orphans),
        orphan_like_sample=severe_orphans[:100],
        phases=phases,
    )


def build_evidence_records(root: Path) -> list[ReportEvidenceRecord]:
    reports_root = root / "reports"
    if not reports_root.exists():
        return []

    records: list[ReportEvidenceRecord] = []
    for path in reports_root.rglob("*.json"):
        if not path.is_file():
            continue
        relative = safe_relative(path, root)
        status, source, parse_error = classify_report_status(relative, path)
        try:
            modified_epoch_ms = int(path.stat().st_mtime * 1000)
        except OSError:
            modified_epoch_ms = 0
        sha: str | None = None
        if status != "malformed_json":
            try:
                sha = file_sha256(path)
            except OSError:
                sha = None
        records.append(
            ReportEvidenceRecord(
                path=relative,
                phase_key=extract_phase_key(relative),
                status=status,
                status_source=source,
                timestamp_token=extract_timestamp_token(relative),
                modified_epoch_ms=modified_epoch_ms,
                sha256=sha,
                parse_error=parse_error,
            )
        )
    return sorted(records, key=lambda item: (item.modified_epoch_ms, item.path), reverse=True)


def select_canonical_records(records: list[ReportEvidenceRecord]) -> list[ReportEvidenceRecord]:
    best: dict[tuple[str, str], ReportEvidenceRecord] = {}
    for record in records:
        phase_key = record.phase_key or "NO_PHASE"
        group = (phase_key, record.status)
        existing = best.get(group)
        if existing is None:
            best[group] = record
            continue
        existing_score = (STATUS_PRIORITY.get(existing.status, 0), existing.modified_epoch_ms, existing.path)
        candidate_score = (STATUS_PRIORITY.get(record.status, 0), record.modified_epoch_ms, record.path)
        if candidate_score > existing_score:
            best[group] = record
    return sorted(best.values(), key=lambda item: (item.phase_key or "", STATUS_PRIORITY.get(item.status, 0), item.modified_epoch_ms), reverse=True)


def build_canonical_evidence_index(root: Path) -> CanonicalEvidenceIndex:
    records = build_evidence_records(root)
    canonical = select_canonical_records(records)
    counts: dict[str, int] = {}
    for record in records:
        counts[record.status] = counts.get(record.status, 0) + 1

    reports_exists = (root / "reports").exists()
    complete = reports_exists and bool(records) and bool(canonical)
    return CanonicalEvidenceIndex(
        complete=complete,
        reports_dir_exists=reports_exists,
        report_count=len(records),
        classified_count=len(records),
        ready_count=counts.get("ready", 0),
        not_ready_count=counts.get("not_ready", 0),
        approval_required_count=counts.get("approval_required", 0),
        execution_evidence_required_count=counts.get("execution_evidence_required", 0),
        snapshot_count=counts.get("snapshot", 0),
        manifest_count=counts.get("manifest", 0),
        unknown_count=counts.get("unknown", 0),
        malformed_json_count=counts.get("malformed_json", 0),
        canonical_count=len(canonical),
        canonical_records=canonical[:250],
    )


def build_bad_evidence_ledger(records: list[ReportEvidenceRecord]) -> BadEvidenceLedger:
    ledger_records: list[dict[str, Any]] = []
    status_conflicts = 0

    for record in records:
        lower_path = record.path.lower()
        reasons: list[str] = []
        if any(token in lower_path for token in BAD_EVIDENCE_TOKENS):
            reasons.append("filename_token")
        if record.status == "malformed_json":
            reasons.append("malformed_json")
        if record.status in {"approval_required", "execution_evidence_required"}:
            reasons.append(record.status)
        if record.status_source.startswith("filename_suffix_over_payload_"):
            reasons.append("filename_payload_status_conflict")
            status_conflicts += 1
        if not reasons:
            continue
        ledger_records.append(
            {
                "path": record.path,
                "phase_key": record.phase_key,
                "status": record.status,
                "status_source": record.status_source,
                "parse_error": record.parse_error,
                "reasons": reasons,
            }
        )

    malformed_count = sum(1 for item in ledger_records if "malformed_json" in item["reasons"])
    approval_count = sum(1 for item in ledger_records if "approval_required" in item["reasons"])
    execution_count = sum(1 for item in ledger_records if "execution_evidence_required" in item["reasons"])

    return BadEvidenceLedger(
        complete=True,
        bad_evidence_count=len(ledger_records),
        malformed_json_count=malformed_count,
        approval_required_count=approval_count,
        execution_evidence_required_count=execution_count,
        status_conflict_count=status_conflicts,
        records=ledger_records[:500],
    )


def find_latest_33a_report(root: Path) -> str | None:
    recovery_root = root / "reports" / "recovery"
    if not recovery_root.exists():
        return None
    candidates = [path for path in recovery_root.glob("4B436633A_project_recovery_baseline_*.json") if path.is_file()]
    if not candidates:
        return None
    candidates.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    return safe_relative(candidates[0], root)


def build_safety_snapshot() -> HygieneSafetySnapshot:
    return HygieneSafetySnapshot(
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        exchange_submit_performed=False,
    )


def build_canonical_evidence_phase_hygiene(root: Path) -> CanonicalEvidencePhaseHygieneReport:
    phase_hygiene = build_phase_hygiene_inventory(root)
    evidence_records = build_evidence_records(root)
    canonical_index = build_canonical_evidence_index(root)
    bad_ledger = build_bad_evidence_ledger(evidence_records)
    safety = build_safety_snapshot()

    status = "READY" if phase_hygiene.complete and canonical_index.complete and bad_ledger.complete else "NOT_READY"
    decision = READY_DECISION if status == "READY" else NOT_READY_DECISION

    return CanonicalEvidencePhaseHygieneReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        decision=decision,
        status=status,
        generated_at_epoch_ms=now_epoch_ms(),
        source_33a_report=find_latest_33a_report(root),
        phase_hygiene_inventory=phase_hygiene,
        canonical_evidence_index=canonical_index,
        bad_evidence_ledger=bad_ledger,
        safety_snapshot=safety,
        recommended_next_phase="4B.4.3.6.6.33C Phase Chain Validator" if status == "READY" else "Fix phase/evidence hygiene blockers before 33C",
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_canonical_evidence_phase_hygiene(root: Path, reports_dir: Path) -> tuple[CanonicalEvidencePhaseHygieneReport, dict[str, Path]]:
    report = build_canonical_evidence_phase_hygiene(root)
    suffix = "ready" if report.status == "READY" else "not_ready"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    paths = {
        "hygiene_report": reports_dir / f"{PATCH_ID}_canonical_evidence_phase_hygiene_{stamp}_{suffix}.json",
        "canonical_evidence_index": reports_dir / f"{PATCH_ID}_canonical_evidence_index_{stamp}.json",
        "bad_evidence_ledger": reports_dir / f"{PATCH_ID}_bad_evidence_ledger_{stamp}.json",
    }
    report_payload = report.to_dict()
    write_json(paths["hygiene_report"], report_payload)
    write_json(paths["canonical_evidence_index"], asdict(report.canonical_evidence_index))
    write_json(paths["bad_evidence_ledger"], asdict(report.bad_evidence_ledger))
    return report, paths


def check_canonical_evidence_phase_hygiene(root: Path) -> dict[str, Any]:
    report = build_canonical_evidence_phase_hygiene(root)
    payload = report.to_dict()
    return {
        "ok": True,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "check_name": "canonical_evidence_phase_hygiene",
        "decision": report.decision,
        "status": report.status,
        "phase_hygiene_complete": report.phase_hygiene_inventory.complete,
        "phase_count": report.phase_hygiene_inventory.phase_count,
        "latest_phase_key": report.phase_hygiene_inventory.latest_phase_key,
        "ignored_noise_count": report.phase_hygiene_inventory.ignored_noise_count,
        "orphan_like_count": report.phase_hygiene_inventory.orphan_like_count,
        "canonical_evidence_complete": report.canonical_evidence_index.complete,
        "report_count": report.canonical_evidence_index.report_count,
        "canonical_count": report.canonical_evidence_index.canonical_count,
        "unknown_count": report.canonical_evidence_index.unknown_count,
        "bad_evidence_count": report.bad_evidence_ledger.bad_evidence_count,
        "malformed_json_count": report.bad_evidence_ledger.malformed_json_count,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "exchange_submit_performed": False,
        "payload_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
    }


def _json_default(value: Any) -> str:
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    if args.check_only:
        payload = check_canonical_evidence_phase_hygiene(root)
    else:
        report, paths = run_canonical_evidence_phase_hygiene(root, Path(args.reports_dir))
        payload = report.to_dict()
        payload["written_reports"] = {key: safe_relative(path.resolve(), root) for key, path in paths.items()}
    print(json.dumps(payload, indent=None if args.once_json else 2, sort_keys=True, ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
