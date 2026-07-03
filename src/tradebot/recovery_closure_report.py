from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436633I"
PATCH_VERSION = "4B.4.3.6.6.33I"
PATCH_NAME = "Recovery Closure Report"

READY_DECISION = "RECOVERY_CLOSURE_REPORT_READY_NEXT_PHASE_LOCKED_NO_RUNTIME_ACTIONS"
NOT_READY_DECISION = "RECOVERY_CLOSURE_REPORT_NOT_READY"

_REQUIRED_FILES = (
    "src/tradebot/recovery_closure_report.py",
    "tools/check_4B436633I_recovery_closure_report.py",
    "tools/run_4B436633I_recovery_closure_report.py",
    "tests/test_recovery_closure_report_4B436633I.py",
    "docs/RECOVERY_CLOSURE_REPORT_4B436633I.md",
    "README_APPLY_4B436633I.txt",
)

_CORE_TAGS = tuple(f"4B.4.3.6.6.33{letter}" for letter in "ABCDEFGHI")

_TRUE_VALUES = {"true", "1", "yes", "y", "on"}
_FALSE_VALUES = {"false", "0", "no", "n", "off", ""}


@dataclass(frozen=True)
class SafetySnapshot:
    approved_for_live_real: bool = False
    approved_for_paper_transition: bool = False
    approved_for_exchange_submit: bool = False
    approved_for_runtime_overlay: bool = False
    exchange_submit_performed: bool = False
    trading_action_performed: bool = False
    training_performed: bool = False
    reload_performed: bool = False
    runtime_overlay_activated: bool = False
    archive_execution_allowed: bool = False
    archive_move_performed: bool = False
    file_delete_performed: bool = False
    destructive_cleanup_performed: bool = False
    next_phase_unlock_performed: bool = False

    @property
    def complete(self) -> bool:
        return not any(asdict(self).values())


@dataclass(frozen=True)
class Source33HGate:
    complete: bool
    report_path: str | None
    decision: str | None
    status: str | None
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    final_no_execution_gate_complete: bool
    human_approval_token_status: str | None
    source_33g_complete: bool
    error: str | None = None


@dataclass(frozen=True)
class PhaseAcceptanceRecord:
    phase_token: str
    label: str
    latest_report_path: str | None
    latest_status: str
    latest_decision: str | None
    report_count: int
    accepted: bool
    acceptance_reason: str
    required_for_closure: bool = True
    superseded_by: str | None = None


@dataclass(frozen=True)
class FinalPhaseAcceptanceMatrix:
    complete: bool
    accepted_for_closure: bool
    required_phase_count: int
    accepted_required_phase_count: int
    observed_phase_count: int
    missing_required_phase_tokens: list[str]
    rejected_required_phase_tokens: list[str]
    records: list[PhaseAcceptanceRecord]


@dataclass(frozen=True)
class GitTagAudit:
    complete: bool
    git_available: bool
    repo_root: str
    head_short: str | None
    branch: str | None
    dirty_worktree_count: int
    dirty_worktree_sample: list[str]
    required_tag_count: int
    present_tag_count: int
    missing_tags: list[str]
    present_tags: list[str]
    audit_warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NextPhaseUnlockPlan:
    complete: bool
    next_phase: str
    unlock_status: str
    unlock_allowed: bool
    unlock_performed: bool
    blocking_conditions: list[str]
    required_operator_actions: list[str]
    recommended_sequence: list[str]
    risk_position: str


@dataclass(frozen=True)
class RecoveryClosureReport:
    patch_id: str
    patch_version: str
    patch_name: str
    generated_at_epoch_ms: int
    status: str
    decision: str
    ok: bool
    source_33h_gate: Source33HGate
    final_phase_acceptance_matrix: FinalPhaseAcceptanceMatrix
    git_tag_audit: GitTagAudit
    next_phase_unlock_plan: NextPhaseUnlockPlan
    safety_snapshot: SafetySnapshot
    required_files_present: bool
    missing_files: list[str]
    py_compile_ok: bool = True
    compile_errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PersistedClosureArtifacts:
    report_path: Path
    acceptance_matrix_path: Path
    git_tag_audit_path: Path
    next_phase_unlock_plan_path: Path


def _repo_root(repo_root: str | Path | None = None) -> Path:
    return Path(repo_root or Path.cwd()).resolve()


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return default


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _latest_matching(root: Path, patterns: Sequence[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(files), key=lambda path: (path.stat().st_mtime_ns, path.as_posix()), reverse=True)


def _status_from_filename(path: Path) -> str:
    name = path.name.lower()
    if "_ready" in name:
        return "READY"
    if "_not_ready" in name:
        return "NOT_READY"
    if "_approval_required" in name:
        return "APPROVAL_REQUIRED"
    if "_execution_evidence_required" in name:
        return "EXECUTION_EVIDENCE_REQUIRED"
    return "UNKNOWN"


def _status_from_payload(payload: Mapping[str, Any] | None, fallback: str) -> str:
    if not payload:
        return fallback
    status = str(payload.get("status") or payload.get("baseline_status") or "").strip().upper()
    if status in {"READY", "NOT_READY", "APPROVAL_REQUIRED", "EXECUTION_EVIDENCE_REQUIRED"}:
        return status
    decision = str(payload.get("decision") or payload.get("baseline_decision") or "").strip().upper()
    if "NOT_READY" in decision:
        return "NOT_READY"
    if "READY" in decision:
        return "READY"
    if payload.get("ok") is True:
        return "READY"
    if payload.get("ok") is False:
        return "NOT_READY"
    return fallback


def _decision_from_payload(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    return _str_or_none(payload.get("decision") or payload.get("baseline_decision"))


def required_files_status(repo_root: Path) -> tuple[bool, list[str]]:
    missing = [path for path in _REQUIRED_FILES if not (repo_root / path).exists()]
    return len(missing) == 0, missing


def _latest_33h_report(root: Path) -> tuple[Path | None, dict[str, Any] | None]:
    candidates = _latest_matching(root, ["reports/recovery/4B436633H_archive_execution_approval_ledger_*_ready.json"])
    for path in candidates:
        payload = _read_json(path)
        if payload is not None:
            return path, payload
    return None, None


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _pick_nested(payload: Mapping[str, Any], paths: Sequence[Sequence[str]], default: Any = None) -> Any:
    for path in paths:
        current: Any = payload
        matched = True
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                matched = False
                break
            current = current[key]
        if matched and current is not None:
            return current
    return default


def _pick_bool_nested(payload: Mapping[str, Any], paths: Sequence[Sequence[str]], default: bool = False) -> bool:
    return _as_bool(_pick_nested(payload, paths, default), default=default)


def _pick_str_nested(payload: Mapping[str, Any], paths: Sequence[Sequence[str]]) -> str | None:
    return _str_or_none(_pick_nested(payload, paths, None))


def _is_sha256(value: str | None) -> bool:
    if value is None or len(value) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def build_source_33h_gate(repo_root: str | Path | None = None) -> Source33HGate:
    root = _repo_root(repo_root)
    report_path, payload = _latest_33h_report(root)
    if report_path is None or payload is None:
        return Source33HGate(
            complete=False,
            report_path=None,
            decision=None,
            status=None,
            manifest_sha256=None,
            immutable_plan_digest=None,
            final_no_execution_gate_complete=False,
            human_approval_token_status=None,
            source_33g_complete=False,
            error="33H READY report not found",
        )

    status = _status_from_payload(payload, _status_from_filename(report_path))
    decision = _decision_from_payload(payload)

    # 33H can appear as a compact stdout summary or as the persisted full run-report.
    # The full report stores decisive fields under source_33g_gate,
    # immutable_plan_digest_ledger, human_approval_token_ledger, and final_no_execution_gate.
    source_33g_complete = _pick_bool_nested(
        payload,
        [
            ("source_33g_complete",),
            ("source_33g_gate", "complete"),
        ],
        default=False,
    )
    final_gate_complete = _pick_bool_nested(
        payload,
        [
            ("final_no_execution_gate_complete",),
            ("final_no_execution_gate", "complete"),
        ],
        default=False,
    )
    immutable_complete = _pick_bool_nested(
        payload,
        [
            ("immutable_plan_digest_complete",),
            ("immutable_plan_digest_ledger", "complete"),
        ],
        default=False,
    )
    manifest_sha256 = _pick_str_nested(
        payload,
        [
            ("manifest_sha256",),
            ("source_33g_gate", "manifest_sha256"),
            ("immutable_plan_digest_ledger", "manifest_sha256"),
        ],
    )
    immutable_digest = _pick_str_nested(
        payload,
        [
            ("immutable_plan_digest",),
            ("immutable_plan_digest_ledger", "plan_digest"),
            ("immutable_plan_digest_ledger", "immutable_plan_digest"),
        ],
    )
    token_status = _pick_str_nested(
        payload,
        [
            ("human_approval_token_status",),
            ("human_approval_token_ledger", "token_status"),
        ],
    )

    safety_paths: dict[str, list[tuple[str, ...]]] = {
        "archive_execution_allowed": [("archive_execution_allowed",), ("final_no_execution_gate", "archive_execution_allowed")],
        "archive_move_performed": [("archive_move_performed",), ("final_no_execution_gate", "archive_move_performed")],
        "file_delete_performed": [("file_delete_performed",), ("final_no_execution_gate", "file_delete_performed")],
        "destructive_cleanup_performed": [("destructive_cleanup_performed",), ("final_no_execution_gate", "destructive_cleanup_performed")],
        "exchange_submit_performed": [("exchange_submit_performed",), ("final_no_execution_gate", "exchange_submit_performed")],
        "trading_action_performed": [("trading_action_performed",), ("final_no_execution_gate", "trading_action_performed")],
        "training_performed": [("training_performed",), ("final_no_execution_gate", "training_performed")],
        "reload_performed": [("reload_performed",), ("final_no_execution_gate", "reload_performed")],
        "runtime_overlay_activated": [("runtime_overlay_activated",), ("final_no_execution_gate", "runtime_overlay_activated")],
        "approved_for_exchange_submit": [("approved_for_exchange_submit",), ("final_no_execution_gate", "approved_for_exchange_submit")],
        "approved_for_live_real": [("approved_for_live_real",), ("final_no_execution_gate", "approved_for_live_real")],
        "approved_for_paper_transition": [("approved_for_paper_transition",), ("final_no_execution_gate", "approved_for_paper_transition")],
        "approved_for_runtime_overlay": [("approved_for_runtime_overlay",), ("final_no_execution_gate", "approved_for_runtime_overlay")],
    }
    safety_ok = all(not _pick_bool_nested(payload, paths, default=False) for paths in safety_paths.values())

    complete = bool(
        status == "READY"
        and decision == "ARCHIVE_EXECUTION_APPROVAL_LEDGER_READY_FINAL_NO_EXECUTION_GATE_LOCKED"
        and source_33g_complete
        and final_gate_complete
        and immutable_complete
        and _is_sha256(manifest_sha256)
        and _is_sha256(immutable_digest)
        and safety_ok
    )

    return Source33HGate(
        complete=complete,
        report_path=_rel(report_path, root),
        decision=decision,
        status=status,
        manifest_sha256=manifest_sha256,
        immutable_plan_digest=immutable_digest,
        final_no_execution_gate_complete=final_gate_complete,
        human_approval_token_status=token_status,
        source_33g_complete=source_33g_complete,
        error=None if complete else "33H report found but closure source gate is incomplete",
    )


def _phase_expectations() -> list[dict[str, Any]]:
    return [
        {
            "token": "4B436633A",
            "label": "Project Recovery Baseline",
            "patterns": ["reports/recovery/4B436633A_project_recovery_baseline_*.json"],
            "required": False,
            "superseded_by": "4B436633B",
        },
        {
            "token": "4B436633B",
            "label": "Canonical Evidence & Phase Hygiene Cleanup",
            "patterns": ["reports/recovery/4B436633B_canonical_evidence_phase_hygiene_*.json"],
            "required": True,
        },
        {
            "token": "4B436633C",
            "label": "Phase Chain Validator",
            "patterns": ["reports/recovery/4B436633C_phase_chain_validator_*.json"],
            "required": True,
        },
        {
            "token": "4B436633D",
            "label": "Runtime Safety Lockdown",
            "patterns": ["reports/recovery/4B436633D_runtime_safety_lockdown_*.json"],
            "required": True,
        },
        {
            "token": "4B436633D-H1",
            "label": "Destructive Endpoint Guard Coverage Hotfix",
            "patterns": ["reports/recovery/4B436633D_H1_destructive_endpoint_guard_hotfix_*.json"],
            "required": True,
        },
        {
            "token": "4B436633E",
            "label": "Status Conflict Resolver",
            "patterns": ["reports/recovery/4B436633E_status_conflict_resolver_*.json"],
            "required": True,
        },
        {
            "token": "4B436633E-H1",
            "label": "Source 33D Completion Gate Hotfix",
            "patterns": ["reports/recovery/4B436633E_H1_source_33d_gate_hotfix_*.json"],
            "required": True,
        },
        {
            "token": "4B436633F",
            "label": "Evidence Retention & Archive Policy",
            "patterns": ["reports/recovery/4B436633F_evidence_retention_archive_policy_*.json"],
            "required": True,
        },
        {
            "token": "4B436633F-H1",
            "label": "Source 33E Completion Gate Hotfix",
            "patterns": ["reports/recovery/4B436633F_H1_source_33e_gate_hotfix_*.json"],
            "required": True,
        },
        {
            "token": "4B436633G",
            "label": "Archive Execution Preflight",
            "patterns": ["reports/recovery/4B436633G_archive_execution_preflight_*.json"],
            "required": True,
        },
        {
            "token": "4B436633G-H1",
            "label": "Source 33F Completion Gate Hotfix",
            "patterns": ["reports/recovery/4B436633G_H1_source_33f_gate_hotfix_*.json"],
            "required": True,
        },
        {
            "token": "4B436633H",
            "label": "Archive Execution Approval Ledger",
            "patterns": ["reports/recovery/4B436633H_archive_execution_approval_ledger_*.json"],
            "required": True,
        },
        {
            "token": "4B436633H-H1",
            "label": "Source 33G Completion Gate Hotfix",
            "patterns": ["reports/recovery/4B436633H_H1_source_33g_gate_hotfix_*.json"],
            "required": True,
        },
    ]


def build_final_phase_acceptance_matrix(repo_root: str | Path | None = None) -> FinalPhaseAcceptanceMatrix:
    root = _repo_root(repo_root)
    records: list[PhaseAcceptanceRecord] = []

    for expectation in _phase_expectations():
        candidates = _latest_matching(root, expectation["patterns"])
        latest_path = candidates[0] if candidates else None
        payload = _read_json(latest_path) if latest_path else None
        fallback_status = _status_from_filename(latest_path) if latest_path else "MISSING"
        latest_status = _status_from_payload(payload, fallback_status) if latest_path else "MISSING"
        latest_decision = _decision_from_payload(payload)
        accepted = latest_status == "READY"
        reason = "latest_report_ready" if accepted else "latest_report_not_ready_or_missing"

        if expectation["token"] == "4B436633A" and latest_path is not None:
            accepted = True
            reason = "baseline_observed_and_superseded_by_canonical_hygiene"

        records.append(
            PhaseAcceptanceRecord(
                phase_token=expectation["token"],
                label=expectation["label"],
                latest_report_path=_rel(latest_path, root) if latest_path else None,
                latest_status=latest_status,
                latest_decision=latest_decision,
                report_count=len(candidates),
                accepted=accepted,
                acceptance_reason=reason,
                required_for_closure=bool(expectation["required"]),
                superseded_by=expectation.get("superseded_by"),
            )
        )

    required_records = [record for record in records if record.required_for_closure]
    missing_required = [record.phase_token for record in required_records if record.latest_status == "MISSING"]
    rejected_required = [record.phase_token for record in required_records if record.latest_status != "MISSING" and not record.accepted]
    accepted_required = [record for record in required_records if record.accepted]
    accepted_for_closure = not missing_required and not rejected_required

    return FinalPhaseAcceptanceMatrix(
        complete=True,
        accepted_for_closure=accepted_for_closure,
        required_phase_count=len(required_records),
        accepted_required_phase_count=len(accepted_required),
        observed_phase_count=sum(1 for record in records if record.latest_report_path),
        missing_required_phase_tokens=missing_required,
        rejected_required_phase_tokens=rejected_required,
        records=records,
    )


def _git_command(root: Path, args: Sequence[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def build_git_tag_audit(repo_root: str | Path | None = None) -> GitTagAudit:
    root = _repo_root(repo_root)
    warnings: list[str] = []
    returncode, inside, stderr = _git_command(root, ["rev-parse", "--is-inside-work-tree"])
    if returncode != 0 or inside.strip().lower() != "true":
        return GitTagAudit(
            complete=True,
            git_available=False,
            repo_root=str(root),
            head_short=None,
            branch=None,
            dirty_worktree_count=0,
            dirty_worktree_sample=[],
            required_tag_count=len(_CORE_TAGS),
            present_tag_count=0,
            missing_tags=list(_CORE_TAGS),
            present_tags=[],
            audit_warnings=[f"git audit unavailable: {stderr or 'not a git work tree'}"],
        )

    _, head_short, head_err = _git_command(root, ["rev-parse", "--short", "HEAD"])
    _, branch, branch_err = _git_command(root, ["branch", "--show-current"])
    tag_rc, tag_stdout, tag_err = _git_command(root, ["tag", "--list"])
    status_rc, status_stdout, status_err = _git_command(root, ["status", "--short"])

    if head_err:
        warnings.append(head_err)
    if branch_err:
        warnings.append(branch_err)
    if tag_rc != 0:
        warnings.append(tag_err or "git tag --list failed")
    if status_rc != 0:
        warnings.append(status_err or "git status --short failed")

    tags = set(tag_stdout.splitlines()) if tag_stdout else set()
    present = [tag for tag in _CORE_TAGS if tag in tags]
    missing = [tag for tag in _CORE_TAGS if tag not in tags]
    dirty = status_stdout.splitlines() if status_stdout else []

    return GitTagAudit(
        complete=True,
        git_available=True,
        repo_root=str(root),
        head_short=head_short or None,
        branch=branch or None,
        dirty_worktree_count=len(dirty),
        dirty_worktree_sample=dirty[:30],
        required_tag_count=len(_CORE_TAGS),
        present_tag_count=len(present),
        missing_tags=missing,
        present_tags=present,
        audit_warnings=warnings,
    )


def build_next_phase_unlock_plan(
    source_33h_gate: Source33HGate,
    acceptance_matrix: FinalPhaseAcceptanceMatrix,
    git_tag_audit: GitTagAudit,
) -> NextPhaseUnlockPlan:
    blockers: list[str] = []
    actions: list[str] = []

    if not source_33h_gate.complete:
        blockers.append("33H final no-execution closure source gate is incomplete")
        actions.append("Re-run and accept 33H/33H-H1 until 33H READY is available")
    if not acceptance_matrix.accepted_for_closure:
        blockers.append("Final phase acceptance matrix has missing or rejected required phases")
        actions.append("Resolve missing/rejected 33A-33H recovery phase evidence before next phase")
    if git_tag_audit.dirty_worktree_count > 0:
        blockers.append("Git working tree has uncommitted recovery artifacts")
        actions.append("Review git status, commit accepted recovery artifacts, then re-run 33I")
    if git_tag_audit.missing_tags:
        blockers.append("Git tag audit has missing 33A-33I recovery tags")
        actions.append("Create/push missing recovery tags or document why historical tags are intentionally absent")
    if not git_tag_audit.git_available:
        actions.append("Run 33I inside the git work tree to obtain complete tag/head audit evidence")

    recommended_sequence = [
        "Confirm 33I report status is READY and no runtime/archive/trading action flags are true",
        "Review final phase acceptance matrix for 33A-33H and hotfix evidence",
        "Review git tag audit; commit current artifacts and push missing accepted tags if required",
        "Keep paper/live/live-real/exchange-submit/runtime-overlay approvals locked false",
        "Start 34A only as a no-order governance/planning phase unless a later explicit operator approval changes scope",
    ]

    unlock_status = (
        "NEXT_PHASE_UNLOCK_PLAN_READY_PENDING_OPERATOR_REVIEW"
        if not blockers
        else "NEXT_PHASE_UNLOCK_BLOCKED_PENDING_OPERATOR_ACTIONS"
    )

    return NextPhaseUnlockPlan(
        complete=True,
        next_phase="4B.4.3.6.6.34A",
        unlock_status=unlock_status,
        unlock_allowed=False,
        unlock_performed=False,
        blocking_conditions=blockers,
        required_operator_actions=actions,
        recommended_sequence=recommended_sequence,
        risk_position="Fail-closed: no trading, no exchange submit, no archive execution, no runtime overlay, no paper/live unlock.",
    )


def build_recovery_closure_report(repo_root: str | Path | None = None) -> RecoveryClosureReport:
    root = _repo_root(repo_root)
    required_files_present, missing_files = required_files_status(root)
    source_33h_gate = build_source_33h_gate(root)
    matrix = build_final_phase_acceptance_matrix(root)
    git_audit = build_git_tag_audit(root)
    next_plan = build_next_phase_unlock_plan(source_33h_gate, matrix, git_audit)
    safety = SafetySnapshot()

    ok = bool(
        required_files_present
        and source_33h_gate.complete
        and matrix.complete
        and matrix.accepted_for_closure
        and git_audit.complete
        and next_plan.complete
        and safety.complete
    )

    return RecoveryClosureReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        generated_at_epoch_ms=_now_ms(),
        status="READY" if ok else "NOT_READY",
        decision=READY_DECISION if ok else NOT_READY_DECISION,
        ok=ok,
        source_33h_gate=source_33h_gate,
        final_phase_acceptance_matrix=matrix,
        git_tag_audit=git_audit,
        next_phase_unlock_plan=next_plan,
        safety_snapshot=safety,
        required_files_present=required_files_present,
        missing_files=missing_files,
    )


def _json_ready(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False, default=_json_ready)
        handle.write("\n")


def write_recovery_closure_report(
    repo_root: str | Path | None = None,
    reports_dir: str | Path | None = None,
) -> tuple[RecoveryClosureReport, PersistedClosureArtifacts]:
    root = _repo_root(repo_root)
    report = build_recovery_closure_report(root)
    out_dir = Path(reports_dir) if reports_dir is not None else root / "reports" / "recovery"
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    suffix = "ready" if report.ok else "not_ready"
    report_path = out_dir / f"4B436633I_recovery_closure_report_{stamp}_{suffix}.json"
    acceptance_path = out_dir / f"4B436633I_final_phase_acceptance_matrix_{stamp}.json"
    git_path = out_dir / f"4B436633I_git_tag_audit_{stamp}.json"
    unlock_path = out_dir / f"4B436633I_next_phase_unlock_plan_{stamp}.json"

    _write_json(report_path, report)
    _write_json(acceptance_path, report.final_phase_acceptance_matrix)
    _write_json(git_path, report.git_tag_audit)
    _write_json(unlock_path, report.next_phase_unlock_plan)

    return report, PersistedClosureArtifacts(
        report_path=report_path,
        acceptance_matrix_path=acceptance_path,
        git_tag_audit_path=git_path,
        next_phase_unlock_plan_path=unlock_path,
    )


def summarize_report(report: RecoveryClosureReport) -> dict[str, Any]:
    return {
        "check_name": "recovery_closure_report",
        "patch_id": report.patch_id,
        "patch_version": report.patch_version,
        "ok": report.ok,
        "status": report.status,
        "decision": report.decision,
        "required_files_present": report.required_files_present,
        "missing_files": report.missing_files,
        "py_compile_ok": report.py_compile_ok,
        "compile_errors": report.compile_errors,
        "source_33h_complete": report.source_33h_gate.complete,
        "source_33h_report": report.source_33h_gate.report_path,
        "source_33h_decision": report.source_33h_gate.decision,
        "manifest_sha256": report.source_33h_gate.manifest_sha256,
        "immutable_plan_digest": report.source_33h_gate.immutable_plan_digest,
        "final_phase_acceptance_matrix_complete": report.final_phase_acceptance_matrix.complete,
        "accepted_for_closure": report.final_phase_acceptance_matrix.accepted_for_closure,
        "required_phase_count": report.final_phase_acceptance_matrix.required_phase_count,
        "accepted_required_phase_count": report.final_phase_acceptance_matrix.accepted_required_phase_count,
        "missing_required_phase_count": len(report.final_phase_acceptance_matrix.missing_required_phase_tokens),
        "rejected_required_phase_count": len(report.final_phase_acceptance_matrix.rejected_required_phase_tokens),
        "git_tag_audit_complete": report.git_tag_audit.complete,
        "git_available": report.git_tag_audit.git_available,
        "git_head_short": report.git_tag_audit.head_short,
        "git_branch": report.git_tag_audit.branch,
        "dirty_worktree_count": report.git_tag_audit.dirty_worktree_count,
        "missing_git_tag_count": len(report.git_tag_audit.missing_tags),
        "present_git_tag_count": report.git_tag_audit.present_tag_count,
        "next_phase": report.next_phase_unlock_plan.next_phase,
        "next_phase_unlock_plan_complete": report.next_phase_unlock_plan.complete,
        "next_phase_unlock_status": report.next_phase_unlock_plan.unlock_status,
        "next_phase_unlock_allowed": report.next_phase_unlock_plan.unlock_allowed,
        "next_phase_unlock_performed": report.next_phase_unlock_plan.unlock_performed,
        "blocking_condition_count": len(report.next_phase_unlock_plan.blocking_conditions),
        "approved_for_live_real": report.safety_snapshot.approved_for_live_real,
        "approved_for_paper_transition": report.safety_snapshot.approved_for_paper_transition,
        "approved_for_exchange_submit": report.safety_snapshot.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.safety_snapshot.approved_for_runtime_overlay,
        "exchange_submit_performed": report.safety_snapshot.exchange_submit_performed,
        "trading_action_performed": report.safety_snapshot.trading_action_performed,
        "training_performed": report.safety_snapshot.training_performed,
        "reload_performed": report.safety_snapshot.reload_performed,
        "runtime_overlay_activated": report.safety_snapshot.runtime_overlay_activated,
        "archive_execution_allowed": report.safety_snapshot.archive_execution_allowed,
        "archive_move_performed": report.safety_snapshot.archive_move_performed,
        "file_delete_performed": report.safety_snapshot.file_delete_performed,
        "destructive_cleanup_performed": report.safety_snapshot.destructive_cleanup_performed,
    }


def summarize_persisted(report: RecoveryClosureReport, artifacts: PersistedClosureArtifacts, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = _repo_root(root)
    summary = summarize_report(report)
    summary.update(
        {
            "report_path": str(artifacts.report_path),
            "final_phase_acceptance_matrix_path": str(artifacts.acceptance_matrix_path),
            "git_tag_audit_path": str(artifacts.git_tag_audit_path),
            "next_phase_unlock_plan_path": str(artifacts.next_phase_unlock_plan_path),
        }
    )
    return summary
