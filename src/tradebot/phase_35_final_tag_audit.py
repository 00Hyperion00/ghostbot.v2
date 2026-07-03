from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436635I"
PATCH_VERSION = "4B.4.3.6.6.35I"
PATCH_NAME = "Phase-35 Final Tag Audit"
CHECK_NAME = "phase_35_final_tag_audit"
READY_DECISION = "PHASE_35_FINAL_TAG_AUDIT_READY_NO_SUBMIT_PHASE_35_FINAL_CLOSED"
NOT_READY_DECISION = "PHASE_35_FINAL_TAG_AUDIT_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.36A"

REQUIRED_REMOTE_TAGS: tuple[str, ...] = tuple(
    f"4B.4.3.6.6.35{suffix}" for suffix in "ABCDEFGH"
)

SOURCE_35H_PATTERN = "4B436635H_runtime_readiness_planning_closure_*_ready.json"

NO_SUBMIT_FALSE_FLAGS: tuple[str, ...] = (
    "approval_performed",
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "archive_execution_allowed",
    "archive_move_performed",
    "collection_authorization_unlocked",
    "collection_preflight_executed",
    "collection_runbook_executed",
    "collection_seal_relaxed",
    "collector_closure_executed",
    "collector_guard_relaxed",
    "collector_scope_relaxed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "dry_run_collection_authorization_performed",
    "dry_run_collector_executed",
    "evidence_collection_started",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "file_delete_performed",
    "file_move_performed",
    "live_environment_enabled",
    "live_real_submit_allowed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "order_submit_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "phase_35_interim_seal_relaxed",
    "private_account_read_performed",
    "private_api_access_allowed",
    "public_data_collection_allowed_now",
    "public_data_dry_run_authorized",
    "public_market_data_collection_performed",
    "reload_performed",
    "report_delete_performed",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "simulated_approval_performed",
    "trading_action_performed",
    "training_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
)

FINAL_FALSE_FLAGS: tuple[str, ...] = (
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_exchange_submit",
    "approved_for_runtime_overlay",
    "exchange_submit_allowed",
    "network_submit_allowed",
    "paper_submit_allowed",
    "live_real_submit_allowed",
    "runtime_overlay_allowed",
    "order_submit_performed",
    "exchange_submit_performed",
    "trading_action_performed",
    "training_performed",
    "reload_performed",
    "runtime_overlay_activated",
    "runtime_evidence_collection_performed",
    "evidence_collection_started",
    "public_market_data_collection_performed",
    "runtime_probe_performed",
    "runtime_health_probe_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "archive_execution_allowed",
    "archive_move_performed",
    "file_delete_performed",
    "file_move_performed",
    "report_delete_performed",
    "destructive_cleanup_performed",
    "deduplication_action_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "paper_environment_enabled",
    "live_environment_enabled",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "phase_35_final_closure_relaxed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return data


def latest_report(reports_dir: Path, pattern: str) -> Path | None:
    if not reports_dir.exists():
        return None
    matches = [path for path in reports_dir.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime_ns, path.name))


def truthy_violations(source: Mapping[str, Any], flags: Iterable[str]) -> list[str]:
    return [name for name in flags if bool(source.get(name, False))]


@dataclass(frozen=True)
class GitState:
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    remote_tags: tuple[str, ...]
    remote_error: str | None


def _run_git(args: Sequence[str], cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def read_git_state(repo_root: Path, remote_tag_names: Iterable[str] | None = None) -> GitState:
    try:
        branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        head_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        tags = tuple(sorted(set(remote_tag_names or ())))
        return GitState(False, None, None, tags, f"git_unavailable:{exc}")

    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result.returncode == 0 else None

    if remote_tag_names is not None:
        return GitState(git_available, branch, head, tuple(sorted(set(remote_tag_names))), None)

    try:
        remote_result = _run_git(["ls-remote", "--tags", "origin", "4B.4.3.6.6.35*"], repo_root, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return GitState(git_available, branch, head, tuple(), f"remote_tag_query_failed:{exc}")

    if remote_result.returncode != 0:
        message = (remote_result.stderr or remote_result.stdout or "unknown git ls-remote failure").strip()
        return GitState(git_available, branch, head, tuple(), message)

    tags: set[str] = set()
    for line in remote_result.stdout.splitlines():
        if "refs/tags/" not in line:
            continue
        ref = line.rsplit("refs/tags/", 1)[-1].strip()
        if ref.endswith("^{}"):
            ref = ref[:-3]
        if ref:
            tags.add(ref)
    return GitState(git_available, branch, head, tuple(sorted(tags)), None)


def build_remote_tag_audit(git_state: GitState) -> dict[str, Any]:
    present = [tag for tag in REQUIRED_REMOTE_TAGS if tag in set(git_state.remote_tags)]
    missing = [tag for tag in REQUIRED_REMOTE_TAGS if tag not in set(git_state.remote_tags)]
    payload: dict[str, Any] = {
        "audit_name": "phase_35_remote_tag_verification",
        "phase_35_required_remote_tags": list(REQUIRED_REMOTE_TAGS),
        "phase_35_required_remote_tag_count": len(REQUIRED_REMOTE_TAGS),
        "phase_35_present_remote_tags": present,
        "phase_35_present_remote_tag_count": len(present),
        "phase_35_missing_remote_tags": missing,
        "phase_35_missing_remote_tag_count": len(missing),
        "phase_35_remote_tag_audit_complete": len(missing) == 0 and git_state.remote_error is None,
        "phase_35_remote_tag_audit_status": "PHASE_35A_35H_REMOTE_TAG_AUDIT_READY" if len(missing) == 0 and git_state.remote_error is None else "PHASE_35A_35H_REMOTE_TAG_AUDIT_NOT_READY",
        "remote_tag_query_error": git_state.remote_error,
    }
    payload["phase_35_remote_tag_audit_digest"] = stable_digest(payload)
    return payload


def build_interim_seal_lock(source_35h: Mapping[str, Any]) -> dict[str, Any]:
    source_violations = truthy_violations(source_35h, NO_SUBMIT_FALSE_FLAGS)
    complete = (
        source_35h.get("status") == "READY"
        and source_35h.get("no_submit_phase_35_interim_sealed") is True
        and source_35h.get("no_submit_phase_35_interim_seal_locked") is True
        and source_35h.get("phase_35_planning_closure_ready") is True
        and int(source_35h.get("phase_35_missing_tag_count", 1)) == 0
        and not source_violations
    )
    payload: dict[str, Any] = {
        "lock_name": "interim_seal_evidence_lock",
        "interim_seal_evidence_lock_complete": complete,
        "interim_seal_evidence_locked": complete,
        "interim_seal_source_report": str(source_35h.get("report_path") or ""),
        "source_35h_no_submit_phase_35_interim_seal_digest": source_35h.get("no_submit_phase_35_interim_seal_digest"),
        "source_35h_phase_35_tag_audit_digest": source_35h.get("phase_35_tag_audit_digest"),
        "source_35h_planning_evidence_acceptance_digest": source_35h.get("planning_evidence_acceptance_digest"),
        "source_35h_safety_violation_count": len(source_violations),
        "source_35h_safety_violations": source_violations,
        "interim_seal_evidence_lock_status": "INTERIM_SEAL_EVIDENCE_LOCKED" if complete else "INTERIM_SEAL_EVIDENCE_LOCK_NOT_READY",
    }
    payload["interim_seal_evidence_lock_digest"] = stable_digest(payload)
    return payload


def build_no_submit_final_closure() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "seal_name": "no_submit_phase_35_final_closure",
        "no_submit_phase_35_final_closure_complete": True,
        "no_submit_phase_35_final_closed": True,
        "no_submit_phase_35_final_closure_locked": True,
        "no_submit_phase_35_final_closure_status": "NO_SUBMIT_PHASE_35_FINAL_CLOSURE_LOCKED",
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "public_market_data_collection_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "destructive_cleanup_performed": False,
        "deduplication_action_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "phase_35_final_closure_relaxed": False,
    }
    payload["no_submit_phase_35_final_closure_digest"] = stable_digest(payload)
    return payload


def evaluate_phase_35_final_tag_audit(
    repo_root: Path,
    reports_dir: Path,
    *,
    remote_tag_names: Iterable[str] | None = None,
    write_reports: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir.resolve()
    repo_root = repo_root.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_35H_PATTERN)
    source_35h: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_35h_report:{SOURCE_35H_PATTERN}")
    else:
        try:
            source_35h = load_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            errors.append(f"invalid_source_35h_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root, remote_tag_names=remote_tag_names)
    remote_tag_audit = build_remote_tag_audit(git_state)
    interim_lock = build_interim_seal_lock(source_35h) if source_35h else {
        "interim_seal_evidence_lock_complete": False,
        "interim_seal_evidence_locked": False,
        "source_35h_safety_violation_count": 0,
        "source_35h_safety_violations": [],
        "interim_seal_evidence_lock_status": "INTERIM_SEAL_EVIDENCE_LOCK_NOT_READY",
        "interim_seal_evidence_lock_digest": stable_digest({"missing_source_35h": True}),
    }
    final_closure = build_no_submit_final_closure()

    if git_state.remote_error:
        errors.append(f"remote_tag_query_error:{git_state.remote_error}")

    source_safety_violations = interim_lock.get("source_35h_safety_violations", [])
    source_35h_complete = (
        bool(source_35h)
        and source_35h.get("status") == "READY"
        and source_35h.get("decision") == "RUNTIME_READINESS_PLANNING_CLOSURE_READY_NO_SUBMIT_PHASE_35_INTERIM_SEALED"
        and source_35h.get("no_submit_phase_35_interim_sealed") is True
        and source_35h.get("no_submit_phase_35_interim_seal_locked") is True
        and source_35h.get("phase_35_planning_closure_ready") is True
        and len(source_safety_violations) == 0
    )

    phase_35_final_closure_ready = (
        source_35h_complete
        and bool(remote_tag_audit["phase_35_remote_tag_audit_complete"])
        and bool(interim_lock["interim_seal_evidence_lock_complete"])
        and bool(final_closure["no_submit_phase_35_final_closure_complete"])
        and not errors
    )

    status = "READY" if phase_35_final_closure_ready else "NOT_READY"
    decision = READY_DECISION if phase_35_final_closure_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": phase_35_final_closure_ready,
        "status": status,
        "decision": decision,
        "errors": errors,
        "check_name": CHECK_NAME,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "git_available": git_state.git_available,
        "git_branch": git_state.git_branch,
        "git_head_short": git_state.git_head_short,
        "source_35h_complete": source_35h_complete,
        "source_35h_status": "SOURCE_35H_READY" if source_35h_complete else "SOURCE_35H_NOT_READY",
        "source_35h_report": str(source_path) if source_path else None,
        "source_35h_decision": source_35h.get("decision"),
        "source_35h_safety_violation_count": int(interim_lock.get("source_35h_safety_violation_count", 0)),
        "source_35h_safety_violations": interim_lock.get("source_35h_safety_violations", []),
        "source_35h_no_submit_phase_35_interim_seal_digest": source_35h.get("no_submit_phase_35_interim_seal_digest"),
        "source_35h_phase_35_tag_audit_digest": source_35h.get("phase_35_tag_audit_digest"),
        "source_35h_planning_evidence_acceptance_digest": source_35h.get("planning_evidence_acceptance_digest"),
        "source_35h_phase_35_present_tag_count": source_35h.get("phase_35_present_tag_count"),
        "source_35h_phase_35_missing_tag_count": source_35h.get("phase_35_missing_tag_count"),
        "phase_34_closed": True,
        "phase_35_planning_only": True,
        "phase_35_final_closure_ready": phase_35_final_closure_ready,
        "phase_35_closed": phase_35_final_closure_ready,
        "runtime_readiness_status": "PHASE_35_FINAL_CLOSED_PLANNING_ONLY_NO_SUBMIT" if phase_35_final_closure_ready else "PHASE_35_FINAL_CLOSURE_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PHASE_35_FINAL_CLOSURE_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_phase_35_final_tag_audit": phase_35_final_closure_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "phase_35_final_tag_audit_path": None,
        "interim_seal_evidence_lock_path": None,
        "no_submit_phase_35_final_closure_path": None,
        "report_path": None,
    }
    result.update(remote_tag_audit)
    result.update(interim_lock)
    result.update(final_closure)

    # Keep the final result explicitly fail-closed even if future payload fields are added.
    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["phase_35_final_closure_relaxed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        tag_audit_path = reports_dir / f"{PATCH_ID}_phase_35_remote_tag_audit_{stamp}.json"
        interim_lock_path = reports_dir / f"{PATCH_ID}_interim_seal_evidence_lock_{stamp}.json"
        final_closure_path = reports_dir / f"{PATCH_ID}_no_submit_phase_35_final_closure_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_phase_35_final_tag_audit_{stamp}_{status.lower()}.json"
        write_json(tag_audit_path, remote_tag_audit)
        write_json(interim_lock_path, interim_lock)
        write_json(final_closure_path, final_closure)
        result["phase_35_final_tag_audit_path"] = str(tag_audit_path)
        result["interim_seal_evidence_lock_path"] = str(interim_lock_path)
        result["no_submit_phase_35_final_closure_path"] = str(final_closure_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write audit and final closure reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_phase_35_final_tag_audit(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
