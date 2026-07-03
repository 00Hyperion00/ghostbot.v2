
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436633H"
PATCH_VERSION = "4B.4.3.6.6.33H"
PATCH_NAME = "Archive Execution Approval Ledger"
READY_DECISION = "ARCHIVE_EXECUTION_APPROVAL_LEDGER_READY_FINAL_NO_EXECUTION_GATE_LOCKED"
NOT_READY_DECISION = "ARCHIVE_EXECUTION_APPROVAL_LEDGER_NOT_READY"

SOURCE_33G_PATTERN = "4B436633G_archive_execution_preflight_*_ready.json"
APPROVAL_TOKEN_ENV = "TRADEBOT_ARCHIVE_APPROVAL_TOKEN"
APPROVAL_TOKEN_PATTERN = re.compile(
    r"^ARCHIVE_APPROVAL_NOEXEC::4B436633G::(?P<digest>[a-f0-9]{64})::(?P<operator>[A-Za-z0-9_.-]{3,64})::(?P<date>\d{8})$"
)


def _now_epoch_ms() -> int:
    return int(time.time() * 1000)


def _utc_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _bool_false(value: Any) -> bool:
    return value is False or value in (0, "0", "false", "False", None)


def _bool_true(value: Any) -> bool:
    return value is True or value in (1, "1", "true", "True")


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class Source33GGate:
    complete: bool
    report_path: str
    status: str | None
    decision: str | None
    manifest_sha256: str | None
    dry_run_archive_move_record_count: int
    dry_run_archive_total_file_count: int
    dry_run_archive_total_size_bytes: int
    rollback_record_count: int
    operator_approval_present: bool
    operator_approval_status: str | None
    failures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HumanApprovalTokenLedger:
    complete: bool
    token_present: bool
    token_source: str
    token_status: str
    expected_token_prefix: str
    expected_plan_digest: str
    parsed_operator: str | None = None
    parsed_date: str | None = None
    token_digest_matches_plan: bool = False
    failures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ImmutablePlanDigestLedger:
    complete: bool
    plan_digest: str
    source_33g_report: str
    manifest_sha256: str | None
    dry_run_archive_move_record_count: int
    dry_run_archive_total_file_count: int
    dry_run_archive_total_size_bytes: int
    rollback_record_count: int
    canonical_payload: dict[str, Any]


@dataclass(frozen=True)
class FinalNoExecutionGate:
    complete: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    destructive_cleanup_performed: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    approved_for_exchange_submit: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_runtime_overlay: bool
    failures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArchiveExecutionApprovalLedgerReport:
    patch_id: str
    patch_version: str
    patch_name: str
    generated_at_epoch_ms: int
    status: str
    decision: str
    ok: bool
    source_33g_gate: Source33GGate
    immutable_plan_digest_ledger: ImmutablePlanDigestLedger
    human_approval_token_ledger: HumanApprovalTokenLedger
    final_no_execution_gate: FinalNoExecutionGate
    archive_execution_approval_ledger_complete: bool
    recommended_next_phase: str
    archive_execution_allowed: bool = False
    archive_move_performed: bool = False
    file_delete_performed: bool = False
    destructive_cleanup_performed: bool = False
    exchange_submit_performed: bool = False
    trading_action_performed: bool = False
    training_performed: bool = False
    reload_performed: bool = False
    runtime_overlay_activated: bool = False
    approved_for_exchange_submit: bool = False
    approved_for_live_real: bool = False
    approved_for_paper_transition: bool = False
    approved_for_runtime_overlay: bool = False


def find_latest_source_33g_report(repo_root: Path, reports_dir: Path | None = None) -> Path | None:
    root = repo_root.resolve()
    base = reports_dir if reports_dir is not None else root / "reports" / "recovery"
    candidates = sorted(base.glob(SOURCE_33G_PATTERN), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def evaluate_source_33g_gate(repo_root: Path, reports_dir: Path | None = None) -> tuple[Source33GGate, dict[str, Any]]:
    """Validate 33G source report using both summary and full run-report schemas."""
    source_path = find_latest_source_33g_report(repo_root, reports_dir)
    if source_path is None:
        return Source33GGate(
            complete=False,
            report_path="",
            status=None,
            decision=None,
            manifest_sha256=None,
            dry_run_archive_move_record_count=0,
            dry_run_archive_total_file_count=0,
            dry_run_archive_total_size_bytes=0,
            rollback_record_count=0,
            operator_approval_present=False,
            operator_approval_status=None,
            failures=["source_33g_ready_report_missing"],
        ), {}

    payload = _read_json(source_path)
    failures: list[str] = []

    def first_value(*paths: tuple[str, ...], default: Any = None) -> Any:
        for path in paths:
            current: Any = payload
            for key in path:
                if not isinstance(current, Mapping) or key not in current:
                    current = None
                    break
                current = current[key]
            if current is not None:
                return current
        return default

    def int_value(*paths: tuple[str, ...]) -> int:
        raw = first_value(*paths, default=0)
        try:
            return int(raw or 0)
        except (TypeError, ValueError):
            return 0

    status = first_value(("status",))
    decision = first_value(("decision",))
    manifest_sha256 = first_value(
        ("manifest_sha256",),
        ("manifest_hash_verification", "manifest_sha256"),
        ("manifest_hash_verification_ledger", "manifest_sha256"),
    )
    move_count = int_value(
        ("dry_run_archive_move_record_count",),
        ("dry_run_archive_move_preview", "record_count"),
        ("dry_run_archive_move_preview", "dry_run_archive_move_record_count"),
    )
    file_count = int_value(
        ("dry_run_archive_total_file_count",),
        ("dry_run_archive_move_preview", "total_file_count"),
        ("dry_run_archive_move_preview", "dry_run_archive_total_file_count"),
    )
    total_size = int_value(
        ("dry_run_archive_total_size_bytes",),
        ("dry_run_archive_move_preview", "total_size_bytes"),
        ("dry_run_archive_move_preview", "dry_run_archive_total_size_bytes"),
    )
    rollback_count = int_value(
        ("rollback_record_count",),
        ("rollback_plan", "rollback_record_count"),
        ("rollback_plan", "record_count"),
    )
    missing_source_count = int_value(
        ("manifest_missing_source_count",),
        ("manifest_hash_verification", "missing_source_count"),
        ("manifest_hash_verification", "manifest_missing_source_count"),
    )
    approval_present_raw = first_value(
        ("operator_approval_present",),
        ("operator_approved_archive_plan_validator", "operator_approval_present"),
        default=False,
    )
    approval_present = bool(approval_present_raw is True)
    approval_status = first_value(
        ("operator_approval_status",),
        ("operator_approved_archive_plan_validator", "operator_approval_status"),
    )

    required_true = {
        "archive_execution_preflight_complete": first_value(("archive_execution_preflight_complete",)),
        "dry_run_archive_move_preview_complete": first_value(
            ("dry_run_archive_move_preview_complete",),
            ("dry_run_archive_move_preview", "complete"),
        ),
        "manifest_hash_verification_complete": first_value(
            ("manifest_hash_verification_complete",),
            ("manifest_hash_verification", "complete"),
        ),
        "rollback_plan_complete": first_value(
            ("rollback_plan_complete",),
            ("rollback_plan", "complete"),
        ),
        "source_33f_complete": first_value(
            ("source_33f_complete",),
            ("source_gate", "complete"),
        ),
    }
    required_false = {
        "archive_execution_allowed": first_value(("archive_execution_allowed",), default=False),
        "archive_move_performed": first_value(("archive_move_performed",), default=False),
        "file_delete_performed": first_value(("file_delete_performed",), default=False),
        "destructive_cleanup_performed": first_value(("destructive_cleanup_performed",), default=False),
        "exchange_submit_performed": first_value(("exchange_submit_performed",), default=False),
        "trading_action_performed": first_value(("trading_action_performed",), default=False),
        "training_performed": first_value(("training_performed",), default=False),
        "reload_performed": first_value(("reload_performed",), default=False),
        "runtime_overlay_activated": first_value(("runtime_overlay_activated",), default=False),
        "approved_for_exchange_submit": first_value(("approved_for_exchange_submit",), default=False),
        "approved_for_live_real": first_value(("approved_for_live_real",), default=False),
        "approved_for_paper_transition": first_value(("approved_for_paper_transition",), default=False),
        "approved_for_runtime_overlay": first_value(("approved_for_runtime_overlay",), default=False),
    }

    if status != "READY":
        failures.append("source_33g_status_not_ready")
    if decision != "ARCHIVE_EXECUTION_PREFLIGHT_READY_DRY_RUN_VALIDATED":
        failures.append("source_33g_decision_not_ready_dry_run_validated")
    if not isinstance(manifest_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256):
        failures.append("source_33g_manifest_sha256_invalid_or_missing")
    if missing_source_count != 0:
        failures.append("source_33g_manifest_missing_source_count_non_zero")
    if move_count <= 0:
        failures.append("source_33g_dry_run_move_record_count_zero")
    if rollback_count <= 0:
        failures.append("source_33g_rollback_record_count_zero")
    if file_count <= 0:
        failures.append("source_33g_total_file_count_zero")

    for field_name, value in required_true.items():
        if not _bool_true(value):
            failures.append(f"source_33g_required_true_failed:{field_name}")
    for field_name, value in required_false.items():
        if not _bool_false(value):
            failures.append(f"source_33g_required_false_failed:{field_name}")

    complete = not failures
    return Source33GGate(
        complete=complete,
        report_path=_rel(source_path.resolve(), repo_root.resolve()),
        status=status if isinstance(status, str) else None,
        decision=decision if isinstance(decision, str) else None,
        manifest_sha256=manifest_sha256 if isinstance(manifest_sha256, str) else None,
        dry_run_archive_move_record_count=move_count,
        dry_run_archive_total_file_count=file_count,
        dry_run_archive_total_size_bytes=total_size,
        rollback_record_count=rollback_count,
        operator_approval_present=approval_present,
        operator_approval_status=approval_status if isinstance(approval_status, str) else None,
        failures=failures,
    ), payload

def build_immutable_plan_digest(source_gate: Source33GGate) -> ImmutablePlanDigestLedger:
    canonical_payload: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "source_patch_id": "4B436633G",
        "source_33g_report": source_gate.report_path,
        "source_33g_decision": source_gate.decision,
        "manifest_sha256": source_gate.manifest_sha256,
        "dry_run_archive_move_record_count": source_gate.dry_run_archive_move_record_count,
        "dry_run_archive_total_file_count": source_gate.dry_run_archive_total_file_count,
        "dry_run_archive_total_size_bytes": source_gate.dry_run_archive_total_size_bytes,
        "rollback_record_count": source_gate.rollback_record_count,
        "no_execution_gate_required": True,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
    }
    digest = _sha256_json(canonical_payload)
    return ImmutablePlanDigestLedger(
        complete=source_gate.complete and bool(digest),
        plan_digest=digest,
        source_33g_report=source_gate.report_path,
        manifest_sha256=source_gate.manifest_sha256,
        dry_run_archive_move_record_count=source_gate.dry_run_archive_move_record_count,
        dry_run_archive_total_file_count=source_gate.dry_run_archive_total_file_count,
        dry_run_archive_total_size_bytes=source_gate.dry_run_archive_total_size_bytes,
        rollback_record_count=source_gate.rollback_record_count,
        canonical_payload=canonical_payload,
    )


def evaluate_human_approval_token(plan_digest: str) -> HumanApprovalTokenLedger:
    expected_prefix = f"ARCHIVE_APPROVAL_NOEXEC::4B436633G::{plan_digest}::"
    raw_token = os.environ.get(APPROVAL_TOKEN_ENV, "").strip()
    if not raw_token:
        return HumanApprovalTokenLedger(
            complete=True,
            token_present=False,
            token_source=APPROVAL_TOKEN_ENV,
            token_status="APPROVAL_TOKEN_NOT_PRESENT_NO_EXECUTION_ONLY",
            expected_token_prefix=expected_prefix,
            expected_plan_digest=plan_digest,
            token_digest_matches_plan=False,
        )

    failures: list[str] = []
    parsed_operator: str | None = None
    parsed_date: str | None = None
    digest_matches = False
    match = APPROVAL_TOKEN_PATTERN.fullmatch(raw_token)
    if match is None:
        failures.append("approval_token_format_invalid")
        status = "APPROVAL_TOKEN_INVALID_NO_EXECUTION_ALLOWED"
    else:
        token_digest = match.group("digest")
        parsed_operator = match.group("operator")
        parsed_date = match.group("date")
        digest_matches = token_digest == plan_digest
        if not digest_matches:
            failures.append("approval_token_digest_mismatch")
            status = "APPROVAL_TOKEN_DIGEST_MISMATCH_NO_EXECUTION_ALLOWED"
        else:
            status = "APPROVAL_TOKEN_RECORDED_NO_EXECUTION_ALLOWED"

    return HumanApprovalTokenLedger(
        complete=not failures,
        token_present=True,
        token_source=APPROVAL_TOKEN_ENV,
        token_status=status,
        expected_token_prefix=expected_prefix,
        expected_plan_digest=plan_digest,
        parsed_operator=parsed_operator,
        parsed_date=parsed_date,
        token_digest_matches_plan=digest_matches,
        failures=failures,
    )


def evaluate_final_no_execution_gate(source_payload: Mapping[str, Any]) -> FinalNoExecutionGate:
    false_fields = {
        "archive_execution_allowed": source_payload.get("archive_execution_allowed", False),
        "archive_move_performed": source_payload.get("archive_move_performed", False),
        "file_delete_performed": source_payload.get("file_delete_performed", False),
        "destructive_cleanup_performed": source_payload.get("destructive_cleanup_performed", False),
        "exchange_submit_performed": source_payload.get("exchange_submit_performed", False),
        "trading_action_performed": source_payload.get("trading_action_performed", False),
        "training_performed": source_payload.get("training_performed", False),
        "reload_performed": source_payload.get("reload_performed", False),
        "runtime_overlay_activated": source_payload.get("runtime_overlay_activated", False),
        "approved_for_exchange_submit": source_payload.get("approved_for_exchange_submit", False),
        "approved_for_live_real": source_payload.get("approved_for_live_real", False),
        "approved_for_paper_transition": source_payload.get("approved_for_paper_transition", False),
        "approved_for_runtime_overlay": source_payload.get("approved_for_runtime_overlay", False),
    }
    failures = [f"final_no_execution_gate_failed:{name}" for name, value in false_fields.items() if not _bool_false(value)]
    return FinalNoExecutionGate(
        complete=not failures,
        archive_execution_allowed=False,
        archive_move_performed=False,
        file_delete_performed=False,
        destructive_cleanup_performed=False,
        exchange_submit_performed=False,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        approved_for_exchange_submit=False,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_runtime_overlay=False,
        failures=failures,
    )


def build_archive_execution_approval_ledger_report(repo_root: Path, reports_dir: Path | None = None) -> ArchiveExecutionApprovalLedgerReport:
    root = repo_root.resolve()
    source_gate, source_payload = evaluate_source_33g_gate(root, reports_dir)
    immutable_plan = build_immutable_plan_digest(source_gate)
    approval_token = evaluate_human_approval_token(immutable_plan.plan_digest)
    no_execution_gate = evaluate_final_no_execution_gate(source_payload)

    complete = source_gate.complete and immutable_plan.complete and approval_token.complete and no_execution_gate.complete
    status = "READY" if complete else "NOT_READY"
    decision = READY_DECISION if complete else NOT_READY_DECISION
    recommended_next_phase = (
        "Proceed to archive execution implementation only after an explicit future execution patch and separate operator approval."
        if complete
        else "Resolve archive approval ledger blockers before continuing."
    )
    return ArchiveExecutionApprovalLedgerReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        generated_at_epoch_ms=_now_epoch_ms(),
        status=status,
        decision=decision,
        ok=complete,
        source_33g_gate=source_gate,
        immutable_plan_digest_ledger=immutable_plan,
        human_approval_token_ledger=approval_token,
        final_no_execution_gate=no_execution_gate,
        archive_execution_approval_ledger_complete=complete,
        recommended_next_phase=recommended_next_phase,
    )


def summarize_report(report: ArchiveExecutionApprovalLedgerReport) -> dict[str, Any]:
    return {
        "check_name": "archive_execution_approval_ledger",
        "patch_id": report.patch_id,
        "patch_version": report.patch_version,
        "status": report.status,
        "decision": report.decision,
        "ok": report.ok,
        "source_33g_complete": report.source_33g_gate.complete,
        "source_33g_report": report.source_33g_gate.report_path,
        "source_33g_decision": report.source_33g_gate.decision,
        "immutable_plan_digest_complete": report.immutable_plan_digest_ledger.complete,
        "immutable_plan_digest": report.immutable_plan_digest_ledger.plan_digest,
        "manifest_sha256": report.immutable_plan_digest_ledger.manifest_sha256,
        "human_approval_token_ledger_complete": report.human_approval_token_ledger.complete,
        "human_approval_token_present": report.human_approval_token_ledger.token_present,
        "human_approval_token_status": report.human_approval_token_ledger.token_status,
        "final_no_execution_gate_complete": report.final_no_execution_gate.complete,
        "archive_execution_approval_ledger_complete": report.archive_execution_approval_ledger_complete,
        "dry_run_archive_move_record_count": report.source_33g_gate.dry_run_archive_move_record_count,
        "dry_run_archive_total_file_count": report.source_33g_gate.dry_run_archive_total_file_count,
        "dry_run_archive_total_size_bytes": report.source_33g_gate.dry_run_archive_total_size_bytes,
        "rollback_record_count": report.source_33g_gate.rollback_record_count,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
    }


def write_archive_execution_approval_ledger_report(repo_root: Path, reports_dir: Path | None = None) -> dict[str, Any]:
    root = repo_root.resolve()
    out_dir = reports_dir if reports_dir is not None else root / "reports" / "recovery"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_archive_execution_approval_ledger_report(root, out_dir)
    stamp = _utc_stamp()
    suffix = "ready" if report.ok else "not_ready"

    report_path = out_dir / f"{PATCH_ID}_archive_execution_approval_ledger_{stamp}_{suffix}.json"
    token_ledger_path = out_dir / f"{PATCH_ID}_human_approval_token_ledger_{stamp}.json"
    digest_ledger_path = out_dir / f"{PATCH_ID}_immutable_plan_digest_ledger_{stamp}.json"
    no_execution_gate_path = out_dir / f"{PATCH_ID}_final_no_execution_gate_{stamp}.json"

    report_path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    token_ledger_path.write_text(json.dumps(asdict(report.human_approval_token_ledger), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    digest_ledger_path.write_text(json.dumps(asdict(report.immutable_plan_digest_ledger), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    no_execution_gate_path.write_text(json.dumps(asdict(report.final_no_execution_gate), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    summary = summarize_report(report)
    summary.update(
        {
            "report_path": str(report_path),
            "human_approval_token_ledger_path": str(token_ledger_path),
            "immutable_plan_digest_ledger_path": str(digest_ledger_path),
            "final_no_execution_gate_path": str(no_execution_gate_path),
        }
    )
    return summary


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    result = write_archive_execution_approval_ledger_report(repo_root, reports_dir) if args.write else summarize_report(build_archive_execution_approval_ledger_report(repo_root, reports_dir))
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
