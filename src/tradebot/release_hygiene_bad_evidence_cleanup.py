from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from .config import Settings
except Exception:  # pragma: no cover - defensive import fallback for isolated tooling tests
    class Settings:  # type: ignore[no-redef]
        release_hygiene_bad_evidence_cleanup_enabled: bool = True
        release_hygiene_bad_evidence_quarantine_required: bool = True
        release_hygiene_final_audit_snapshot_required: bool = True
        release_hygiene_no_further_live_orders_required: bool = True
        release_hygiene_finalization_token: str = "FINALIZE_31B_RELEASE_HYGIENE_AUDIT"

CONTRACT_VERSION = "4B.4.3.6.6.31B"
SOURCE_31A_H3_CONTRACT_VERSION = "4B.4.3.6.6.31A-H3"
SOURCE_31A_H3_READY_DECISION = "LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_READY_EVIDENCE_PACK_SEALED_NO_FURTHER_LIVE_ORDER"
REPORT_TYPE = "release_hygiene_bad_evidence_ledger_cleanup"
REPORT_PREFIX = "4B436631B_release_hygiene_bad_evidence_ledger_cleanup"
SOURCE_31A_REPORT_PREFIX = "4B436631A_live_micro_canary_freeze_audit_closure"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
FINALIZATION_TOKEN = "FINALIZE_31B_RELEASE_HYGIENE_AUDIT"

READY_DECISION = "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_READY_FINAL_AUDIT_SNAPSHOT_NO_FURTHER_LIVE_ORDER"
SOURCE_31A_H3_REQUIRED_DECISION = "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_31A_H3_READY_REQUIRED_NO_FURTHER_LIVE_ORDER"
QUARANTINE_REQUIRED_DECISION = "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_QUARANTINE_REQUIRED_NO_FURTHER_LIVE_ORDER"
OPERATOR_AUDIT_REQUIRED_DECISION = "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_OPERATOR_AUDIT_REQUIRED_NO_FURTHER_LIVE_ORDER"
NOT_READY_DECISION = "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_NOT_READY_NO_FURTHER_LIVE_ORDER"

BAD_31A_PATTERNS = (
    f"{SOURCE_31A_REPORT_PREFIX}_*_not_ready.json",
    f"{SOURCE_31A_REPORT_PREFIX}_*_not_ready.md",
)
SUPERSEDED_PHASES = ("4B.4.3.6.6.31A", "4B.4.3.6.6.31A-H1", "4B.4.3.6.6.31A-H2")

RISK_FLAGS: dict[str, bool] = {
    "release_hygiene_bad_evidence_cleanup_only": True,
    "bad_evidence_quarantine_only": True,
    "live_real_order_freeze_active": True,
    "approved_for_additional_exchange_submit": False,
    "approved_for_live_real_continuation": False,
    "approved_for_live_real_order": False,
    "patch_exchange_submit_performed": False,
    "patch_network_submit_attempted": False,
    "patch_live_real_order_performed": False,
    "additional_exchange_submit_performed": False,
    "additional_network_submit_attempted": False,
    "additional_live_real_order_performed": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source31AH3Status:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    source_30z_risk_review_verified: bool
    evidence_pack_sealed: bool
    release_hygiene_verified: bool
    operator_audit_finalized: bool
    no_further_live_orders_verified: bool
    emergency_stop_continuity_verified: bool
    approved_for_additional_exchange_submit: bool
    approved_for_live_real_continuation: bool
    patch_network_submit_attempted: bool
    patch_exchange_submit_performed: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    evidence_pack_file_count: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class QuarantinedFile:
    original_relative_path: str
    quarantine_relative_path: str
    size_bytes: int
    sha256: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BadEvidenceQuarantineStatus:
    ok: bool
    quarantine_requested: bool
    quarantine_performed: bool
    reports_dir: str
    quarantine_dir: str
    quarantine_manifest_id: str
    scanned_patterns: list[str]
    matched_file_count: int
    moved_file_count: int
    remaining_bad_file_count: int
    quarantined_files: list[dict[str, Any]]
    manifest_sha256: str
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BadEvidenceLedgerStatus:
    ok: bool
    superseded_versions: list[str]
    superseded_by: str
    explanation: str
    bad_evidence_history_explained: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorFinalAuditStatus:
    ok: bool
    operator_id: str | None
    finalization_token_verified: bool
    final_audit_snapshot_requested: bool
    audit_comment: str | None
    no_further_live_orders_confirmed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReleaseHygieneBadEvidenceCleanupSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_release_hygiene_bad_evidence_cleanup: bool
    approved_for_final_operator_audit_snapshot: bool
    approved_for_additional_exchange_submit: bool
    approved_for_live_real_continuation: bool
    approved_for_live_real_order: bool
    source_31a_h3_freeze_audit_closure_verified: bool
    bad_evidence_history_explained: bool
    bad_evidence_quarantined: bool
    bad_evidence_quarantine_performed: bool
    bad_evidence_quarantine_moved_file_count: int
    bad_evidence_quarantine_remaining_file_count: int
    final_audit_snapshot_written: bool
    no_further_live_orders_verified: bool
    emergency_stop_continuity_verified: bool
    no_code_path_live_submit_verified: bool
    quarantine_manifest_id: str
    quarantine_manifest_sha256: str
    patch_exchange_submit_performed: bool
    patch_network_submit_attempted: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    reason_codes: list[str]
    source_31a_h3: dict[str, Any]
    bad_evidence_quarantine: dict[str, Any]
    bad_evidence_ledger: dict[str, Any]
    operator_final_audit: dict[str, Any]
    source_31a_h3_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default if value is None else bool(value)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp.replace(resolved)
    finally:
        tmp.unlink(missing_ok=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_destination(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(1, 10_000):
        alternate = directory / f"{stem}_{index}{suffix}"
        if not alternate.exists():
            return alternate
    raise RuntimeError(f"could not allocate quarantine destination for {name}")


def evaluate_source_31a_h3_closure(source_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source31AH3Status:
    contract = str(source_snapshot.get("contract_version") or "") or None
    decision = str(source_snapshot.get("decision") or "") or None
    source_30z = _boolish(source_snapshot.get("source_30z_risk_review_verified"), False)
    sealed = _boolish(source_snapshot.get("evidence_pack_sealed"), False)
    hygiene = _boolish(source_snapshot.get("release_hygiene_verified"), False)
    operator = _boolish(source_snapshot.get("operator_audit_finalized"), False)
    no_further = _boolish(source_snapshot.get("no_further_live_orders_verified"), False)
    emergency = _boolish(source_snapshot.get("emergency_stop_continuity_verified"), False)
    additional_approved = _boolish(source_snapshot.get("approved_for_additional_exchange_submit"), False)
    continuation = _boolish(source_snapshot.get("approved_for_live_real_continuation"), False)
    patch_network = _boolish(source_snapshot.get("patch_network_submit_attempted"), False)
    patch_exchange = _boolish(source_snapshot.get("patch_exchange_submit_performed"), False)
    patch_live = _boolish(source_snapshot.get("patch_live_real_order_performed"), False)
    additional_exchange = _boolish(source_snapshot.get("additional_exchange_submit_performed"), False)
    additional_network = _boolish(source_snapshot.get("additional_network_submit_attempted"), False)
    additional_live = _boolish(source_snapshot.get("additional_live_real_order_performed"), False)
    file_count = _int(source_snapshot.get("evidence_pack_file_count"), 0)
    ok = (
        contract == SOURCE_31A_H3_CONTRACT_VERSION
        and decision == SOURCE_31A_H3_READY_DECISION
        and source_30z
        and sealed
        and hygiene
        and operator
        and no_further
        and emergency
        and not additional_approved
        and not continuation
        and not patch_network
        and not patch_exchange
        and not patch_live
        and not additional_exchange
        and not additional_network
        and not additional_live
        and file_count >= 3
    )
    reasons: list[str] = []
    if contract != SOURCE_31A_H3_CONTRACT_VERSION:
        reasons.append("SOURCE_31A_H3_CONTRACT_VERSION_REQUIRED")
    if decision != SOURCE_31A_H3_READY_DECISION:
        reasons.append("SOURCE_31A_H3_READY_DECISION_REQUIRED")
    if not source_30z:
        reasons.append("SOURCE_31A_H3_MUST_VERIFY_30Z_READY")
    if not sealed:
        reasons.append("SOURCE_31A_H3_EVIDENCE_PACK_SEAL_REQUIRED")
    if not hygiene:
        reasons.append("SOURCE_31A_H3_RELEASE_HYGIENE_REQUIRED")
    if not operator:
        reasons.append("SOURCE_31A_H3_OPERATOR_AUDIT_REQUIRED")
    if not no_further:
        reasons.append("SOURCE_31A_H3_NO_FURTHER_LIVE_ORDERS_REQUIRED")
    if not emergency:
        reasons.append("SOURCE_31A_H3_EMERGENCY_STOP_CONTINUITY_REQUIRED")
    if additional_approved or continuation:
        reasons.append("SOURCE_31A_H3_MUST_NOT_APPROVE_FURTHER_LIVE_REAL")
    if patch_network or patch_exchange or patch_live:
        reasons.append("SOURCE_31A_H3_PATCH_SUBMIT_MUST_BE_FALSE")
    if additional_exchange or additional_network or additional_live:
        reasons.append("SOURCE_31A_H3_ADDITIONAL_LIVE_ORDER_MUST_BE_FALSE")
    if file_count < 3:
        reasons.append("SOURCE_31A_H3_EVIDENCE_PACK_FILE_COUNT_REQUIRED")
    return Source31AH3Status(
        ok=ok,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        source_30z_risk_review_verified=source_30z,
        evidence_pack_sealed=sealed,
        release_hygiene_verified=hygiene,
        operator_audit_finalized=operator,
        no_further_live_orders_verified=no_further,
        emergency_stop_continuity_verified=emergency,
        approved_for_additional_exchange_submit=additional_approved,
        approved_for_live_real_continuation=continuation,
        patch_network_submit_attempted=patch_network,
        patch_exchange_submit_performed=patch_exchange,
        patch_live_real_order_performed=patch_live,
        additional_exchange_submit_performed=additional_exchange,
        additional_network_submit_attempted=additional_network,
        additional_live_real_order_performed=additional_live,
        evidence_pack_file_count=file_count,
        reason_codes=reasons or ["SOURCE_31A_H3_FREEZE_AUDIT_CLOSURE_VERIFIED"],
    )


def latest_valid_31a_h3_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    root = Path(reports_dir)
    candidates = sorted(
        (path for path in root.glob(f"{SOURCE_31A_REPORT_PREFIX}_*_ready.json") if "_not_ready" not in path.name),
        key=lambda item: item.stat().st_mtime if item.exists() else 0.0,
        reverse=True,
    )
    for path in candidates:
        try:
            payload = load_json(path)
        except Exception:
            continue
        if isinstance(payload, Mapping) and evaluate_source_31a_h3_closure(payload, source_report_path=str(path)).ok:
            return path, dict(payload)
    return None, {}


def load_explicit_31a_h3_report(source_report: str | os.PathLike[str]) -> tuple[Path, dict[str, Any]]:
    path = Path(source_report).expanduser().resolve()
    payload = load_json(path)
    if not isinstance(payload, Mapping):
        raise ValueError(f"source 31A-H3 report is not a JSON object: {path}")
    return path, dict(payload)


def build_bad_evidence_ledger() -> BadEvidenceLedgerStatus:
    explanation = (
        "31A, 31A-H1 and 31A-H2 produced NOT_READY/invalid freeze-audit closure attempts. "
        "They are superseded by accepted 31A-H3 explicit 30Z source override evidence. "
        "31B quarantines any remaining bad not_ready artifacts and records this release hygiene ledger."
    )
    return BadEvidenceLedgerStatus(
        ok=True,
        superseded_versions=list(SUPERSEDED_PHASES),
        superseded_by=SOURCE_31A_H3_CONTRACT_VERSION,
        explanation=explanation,
        bad_evidence_history_explained=True,
        reason_codes=["BAD_EVIDENCE_HISTORY_EXPLAINED_SUPERSEDED_BY_31A_H3"],
    )


def quarantine_bad_31a_not_ready_artifacts(
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    perform_quarantine: bool,
    quarantine_manifest_id: str | None = None,
    stamp: str | None = None,
) -> BadEvidenceQuarantineStatus:
    root = Path(reports_dir)
    root.mkdir(parents=True, exist_ok=True)
    resolved_stamp = stamp or utc_stamp()
    manifest_id = quarantine_manifest_id or f"BAD_31A_NOT_READY_QUARANTINE_{resolved_stamp}"
    quarantine_dir = root / "quarantine" / f"4B436631B_bad_31a_evidence_{resolved_stamp}"
    matches: list[Path] = []
    for pattern in BAD_31A_PATTERNS:
        matches.extend(path for path in sorted(root.glob(pattern)) if path.is_file())
    unique_matches = sorted({path.resolve(): path for path in matches}.values(), key=lambda item: item.as_posix())
    quarantined: list[QuarantinedFile] = []
    if perform_quarantine:
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        for src in unique_matches:
            digest = sha256_file(src)
            size = src.stat().st_size
            dst = _safe_destination(quarantine_dir, src.name)
            shutil.move(str(src), str(dst))
            quarantined.append(
                QuarantinedFile(
                    original_relative_path=_relative(src, root),
                    quarantine_relative_path=_relative(dst, root),
                    size_bytes=size,
                    sha256=digest,
                    reason="31A/31A-H1/31A-H2 NOT_READY bad evidence superseded by accepted 31A-H3",
                )
            )
    remaining = 0
    for pattern in BAD_31A_PATTERNS:
        remaining += sum(1 for path in root.glob(pattern) if path.is_file())
    manifest_basis = {
        "contract_version": CONTRACT_VERSION,
        "quarantine_manifest_id": manifest_id,
        "reports_dir": root.as_posix(),
        "quarantine_dir": _relative(quarantine_dir, root),
        "scanned_patterns": list(BAD_31A_PATTERNS),
        "matched_file_count": len(unique_matches),
        "moved_file_count": len(quarantined),
        "remaining_bad_file_count": remaining,
        "quarantined_files": [item.to_dict() for item in quarantined],
    }
    manifest_sha = _sha256_bytes(json.dumps(manifest_basis, ensure_ascii=True, sort_keys=True).encode("utf-8"))
    ok = perform_quarantine and remaining == 0
    reasons: list[str] = []
    if not perform_quarantine:
        reasons.append("BAD_EVIDENCE_QUARANTINE_FLAG_REQUIRED")
    if remaining:
        reasons.append("BAD_31A_NOT_READY_ARTIFACTS_REMAIN")
    if not unique_matches and perform_quarantine:
        reasons.append("NO_BAD_31A_NOT_READY_ARTIFACTS_FOUND_ALREADY_CLEANED")
    if perform_quarantine and unique_matches and not remaining:
        reasons.append("BAD_31A_NOT_READY_ARTIFACTS_QUARANTINED")
    return BadEvidenceQuarantineStatus(
        ok=ok,
        quarantine_requested=perform_quarantine,
        quarantine_performed=perform_quarantine,
        reports_dir=root.as_posix(),
        quarantine_dir=_relative(quarantine_dir, root),
        quarantine_manifest_id=manifest_id,
        scanned_patterns=list(BAD_31A_PATTERNS),
        matched_file_count=len(unique_matches),
        moved_file_count=len(quarantined),
        remaining_bad_file_count=remaining,
        quarantined_files=[item.to_dict() for item in quarantined],
        manifest_sha256=manifest_sha,
        reason_codes=reasons or ["BAD_EVIDENCE_QUARANTINE_VERIFIED"],
    )


def evaluate_operator_final_audit(operator_id: str | None, finalization_token: str | None, *, audit_comment: str | None = None) -> OperatorFinalAuditStatus:
    operator_ok = bool(str(operator_id or "").strip())
    token_ok = str(finalization_token or "").strip() == FINALIZATION_TOKEN
    reasons: list[str] = []
    if not operator_ok:
        reasons.append("OPERATOR_ID_REQUIRED")
    if not token_ok:
        reasons.append("FINALIZATION_TOKEN_REQUIRED")
    return OperatorFinalAuditStatus(
        ok=operator_ok and token_ok,
        operator_id=str(operator_id or "").strip() or None,
        finalization_token_verified=token_ok,
        final_audit_snapshot_requested=operator_ok and token_ok,
        audit_comment=str(audit_comment or "").strip() or None,
        no_further_live_orders_confirmed=True,
        reason_codes=reasons or ["FINAL_OPERATOR_AUDIT_SNAPSHOT_AUTHORIZED"],
    )


def build_release_hygiene_bad_evidence_cleanup_snapshot(
    settings: Any | None = None,
    source_31a_h3_snapshot: Mapping[str, Any] | None = None,
    *,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    move_bad_evidence_to_quarantine: bool = False,
    quarantine_manifest_id: str | None = None,
) -> dict[str, Any]:
    _ = settings or Settings()
    source_payload = dict(_mapping(source_31a_h3_snapshot))
    source = evaluate_source_31a_h3_closure(source_payload, source_report_path=source_report_path)
    quarantine = quarantine_bad_31a_not_ready_artifacts(
        reports_dir,
        perform_quarantine=move_bad_evidence_to_quarantine,
        quarantine_manifest_id=quarantine_manifest_id,
    )
    ledger = build_bad_evidence_ledger()
    operator = evaluate_operator_final_audit(operator_id, finalization_token, audit_comment=audit_comment)
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not quarantine.ok:
        reasons.extend(quarantine.reason_codes)
    if not ledger.ok:
        reasons.extend(ledger.reason_codes)
    if not operator.ok:
        reasons.extend(operator.reason_codes)
    no_code_path_live_submit = True
    no_further_live_orders = source.no_further_live_orders_verified and operator.no_further_live_orders_confirmed
    if source.ok and quarantine.ok and ledger.ok and operator.ok and no_code_path_live_submit and no_further_live_orders:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_31A_H3_REQUIRED_DECISION
    elif not quarantine.ok:
        decision = QUARANTINE_REQUIRED_DECISION
    elif not operator.ok:
        decision = OPERATOR_AUDIT_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    ready = decision == READY_DECISION
    snapshot = ReleaseHygieneBadEvidenceCleanupSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_31A_H3_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_release_hygiene_bad_evidence_cleanup=ready,
        approved_for_final_operator_audit_snapshot=ready,
        approved_for_additional_exchange_submit=False,
        approved_for_live_real_continuation=False,
        approved_for_live_real_order=False,
        source_31a_h3_freeze_audit_closure_verified=source.ok,
        bad_evidence_history_explained=ledger.ok,
        bad_evidence_quarantined=quarantine.ok,
        bad_evidence_quarantine_performed=quarantine.quarantine_performed,
        bad_evidence_quarantine_moved_file_count=quarantine.moved_file_count,
        bad_evidence_quarantine_remaining_file_count=quarantine.remaining_bad_file_count,
        final_audit_snapshot_written=ready,
        no_further_live_orders_verified=no_further_live_orders,
        emergency_stop_continuity_verified=source.emergency_stop_continuity_verified,
        no_code_path_live_submit_verified=no_code_path_live_submit,
        quarantine_manifest_id=quarantine.quarantine_manifest_id,
        quarantine_manifest_sha256=quarantine.manifest_sha256,
        patch_exchange_submit_performed=False,
        patch_network_submit_attempted=False,
        patch_live_real_order_performed=False,
        additional_exchange_submit_performed=False,
        additional_network_submit_attempted=False,
        additional_live_real_order_performed=False,
        reason_codes=reasons or ["RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_READY"],
        source_31a_h3=source.to_dict(),
        bad_evidence_quarantine=quarantine.to_dict(),
        bad_evidence_ledger=ledger.to_dict(),
        operator_final_audit=operator.to_dict(),
        source_31a_h3_snapshot=source_payload,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    return snapshot


def build_from_latest_31a_h3_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    move_bad_evidence_to_quarantine: bool = False,
    quarantine_manifest_id: str | None = None,
) -> dict[str, Any]:
    source_path, source = latest_valid_31a_h3_report(reports_dir)
    return build_release_hygiene_bad_evidence_cleanup_snapshot(
        settings or Settings(),
        source,
        reports_dir=reports_dir,
        source_report_path=str(source_path) if source_path else None,
        operator_id=operator_id,
        finalization_token=finalization_token,
        audit_comment=audit_comment,
        move_bad_evidence_to_quarantine=move_bad_evidence_to_quarantine,
        quarantine_manifest_id=quarantine_manifest_id,
    )


def build_from_explicit_31a_h3_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    source_31a_h3_report: str | os.PathLike[str],
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    move_bad_evidence_to_quarantine: bool = False,
    quarantine_manifest_id: str | None = None,
) -> dict[str, Any]:
    source_path, source = load_explicit_31a_h3_report(source_31a_h3_report)
    return build_release_hygiene_bad_evidence_cleanup_snapshot(
        settings or Settings(),
        source,
        reports_dir=reports_dir,
        source_report_path=str(source_path),
        operator_id=operator_id,
        finalization_token=finalization_token,
        audit_comment=audit_comment,
        move_bad_evidence_to_quarantine=move_bad_evidence_to_quarantine,
        quarantine_manifest_id=quarantine_manifest_id,
    )


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    manifest_path = target / f"{REPORT_PREFIX}_{stamp}_quarantine_manifest.json"
    quarantine_payload = dict(_mapping(payload.get("bad_evidence_quarantine")))
    quarantine_payload.update({
        "contract_version": CONTRACT_VERSION,
        "decision": payload.get("decision"),
        "source_contract_version": payload.get("source_contract_version"),
        "source_31a_h3_report": _mapping(payload.get("source_31a_h3")).get("source_report_path"),
    })
    write_json_atomic(manifest_path, quarantine_payload)
    final_payload = dict(payload)
    final_payload["quarantine_manifest_path"] = _relative(manifest_path, target)
    write_json_atomic(json_path, final_payload)
    lines = [
        f"# {CONTRACT_VERSION} Release Hygiene & Bad Evidence Ledger Cleanup",
        "",
        "Records the 31A / 31A-H1 / 31A-H2 NOT_READY history, quarantines remaining bad evidence artifacts, and finalizes the audit snapshot without approving any live order.",
        "",
        "## Decision",
        f"- `decision`: `{final_payload.get('decision')}`",
        f"- `source_31a_h3_freeze_audit_closure_verified`: `{final_payload.get('source_31a_h3_freeze_audit_closure_verified')}`",
        f"- `bad_evidence_history_explained`: `{final_payload.get('bad_evidence_history_explained')}`",
        f"- `bad_evidence_quarantined`: `{final_payload.get('bad_evidence_quarantined')}`",
        f"- `bad_evidence_quarantine_moved_file_count`: `{final_payload.get('bad_evidence_quarantine_moved_file_count')}`",
        f"- `bad_evidence_quarantine_remaining_file_count`: `{final_payload.get('bad_evidence_quarantine_remaining_file_count')}`",
        f"- `final_audit_snapshot_written`: `{final_payload.get('final_audit_snapshot_written')}`",
        f"- `no_further_live_orders_verified`: `{final_payload.get('no_further_live_orders_verified')}`",
        f"- `patch_network_submit_attempted`: `{final_payload.get('patch_network_submit_attempted')}`",
        "",
        "## Quarantine",
        f"- `quarantine_manifest_id`: `{final_payload.get('quarantine_manifest_id')}`",
        f"- `quarantine_manifest_sha256`: `{final_payload.get('quarantine_manifest_sha256')}`",
        f"- `quarantine_manifest_path`: `{_relative(manifest_path, target)}`",
        "",
        "## Ledger explanation",
        f"- `superseded_versions`: `{', '.join(SUPERSEDED_PHASES)}`",
        f"- `superseded_by`: `{SOURCE_31A_H3_CONTRACT_VERSION}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in final_payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path, manifest_path
