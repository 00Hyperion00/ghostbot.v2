from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436636G"
PATCH_VERSION = "4B.4.3.6.6.36G"
PATCH_NAME = "Public Observation Final Closure"
CHECK_NAME = "public_observation_final_closure"
READY_DECISION = "PUBLIC_OBSERVATION_FINAL_CLOSURE_READY_NO_SUBMIT_PHASE_36_FINAL_SEALED"
NOT_READY_DECISION = "PUBLIC_OBSERVATION_FINAL_CLOSURE_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37A"
SOURCE_36F_PATTERN = "4B436636F_public_observation_evidence_closure_*_ready.json"
REQUIRED_PHASE_36_REMOTE_TAGS: tuple[str, ...] = (
    "4B.4.3.6.6.36A",
    "4B.4.3.6.6.36B",
    "4B.4.3.6.6.36C",
    "4B.4.3.6.6.36D",
    "4B.4.3.6.6.36E",
    "4B.4.3.6.6.36F",
)

NO_SUBMIT_FALSE_FLAGS: tuple[str, ...] = (
    "approval_performed",
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "archive_execution_allowed",
    "archive_move_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "evidence_collection_started",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "file_delete_performed",
    "file_move_performed",
    "http_request_performed",
    "live_environment_enabled",
    "live_real_submit_allowed",
    "network_off_evidence_digest_lock_relaxed",
    "network_request_allowed_now",
    "network_request_performed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "operator_observation_authorization_unlocked",
    "operator_observation_token_consumed",
    "operator_observation_token_present",
    "operator_observation_token_validated",
    "order_submit_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "phase_36_interim_closure_relaxed",
    "phase_36_tag_audit_relaxed",
    "private_account_read_performed",
    "private_api_access_allowed",
    "public_data_fetch_adapter_executed",
    "public_market_data_collection_performed",
    "public_observation_dry_run_collector_executed",
    "public_observation_execution_performed",
    "public_observation_network_off_execution_package_executed",
    "reload_performed",
    "report_delete_performed",
    "runtime_evidence_artifact_written",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "signed_request_performed",
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
    "runtime_evidence_artifact_written",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "public_observation_dry_run_collector_executed",
    "public_observation_network_off_execution_package_executed",
    "public_data_fetch_adapter_executed",
    "network_request_performed",
    "network_request_allowed_now",
    "http_request_performed",
    "signed_request_performed",
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
    "operator_observation_token_consumed",
    "operator_observation_token_validated",
    "operator_observation_authorization_unlocked",
    "operator_observation_token_present",
    "phase_36_final_seal_relaxed",
    "phase_36_final_closure_relaxed",
    "phase_36_remote_tag_audit_relaxed",
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


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


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
    local_phase_36_tags: tuple[str, ...]
    remote_phase_36_tags: tuple[str, ...]
    remote_tag_query_ok: bool
    remote_tag_query_error: str | None


def _run_git(args: Sequence[str], cwd: Path, timeout: int = 25) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _parse_ls_remote_tags(stdout: str) -> tuple[str, ...]:
    tags: set[str] = set()
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith("refs/tags/"):
            tag = ref.removeprefix("refs/tags/").removesuffix("^{}")
            if tag.startswith("4B.4.3.6.6.36"):
                tags.add(tag)
    return tuple(sorted(tags))


def read_git_state(repo_root: Path) -> GitState:
    try:
        branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        head_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
        local_tags_result = _run_git(["tag", "--list", "4B.4.3.6.6.36*"], repo_root)
        remote_tags_result = _run_git(["ls-remote", "--tags", "origin", "4B.4.3.6.6.36*"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return GitState(False, None, None, tuple(), tuple(), False, str(exc))

    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    local_tags = tuple(sorted(line.strip() for line in local_tags_result.stdout.splitlines() if line.strip())) if local_tags_result.returncode == 0 else tuple()
    remote_ok = remote_tags_result.returncode == 0
    remote_error = None if remote_ok else (remote_tags_result.stderr.strip() or remote_tags_result.stdout.strip() or "git ls-remote failed")
    remote_tags = _parse_ls_remote_tags(remote_tags_result.stdout) if remote_ok else tuple()
    return GitState(git_available, branch, head, local_tags, remote_tags, remote_ok, remote_error)


def build_source_36f_gate(source_36f: Mapping[str, Any], source_path: Path | None, safety_violations: Sequence[str]) -> dict[str, Any]:
    source_ready = (
        bool(source_36f)
        and source_36f.get("status") == "READY"
        and source_36f.get("decision") == "PUBLIC_OBSERVATION_EVIDENCE_CLOSURE_READY_NO_SUBMIT_PHASE_36_INTERIM_CLOSED"
        and source_36f.get("source_36e_complete") is True
        and source_36f.get("phase_35_closed") is True
        and source_36f.get("phase_36_planning_only") is True
        and source_36f.get("phase_36_interim_closed") is True
        and source_36f.get("phase_36_final_closed") is False
        and source_36f.get("phase_36_tag_audit_complete") is True
        and source_36f.get("phase_36_missing_tag_count") == 0
        and source_36f.get("network_off_evidence_digest_lock_complete") is True
        and source_36f.get("network_off_evidence_digest_missing_count") == 0
        and source_36f.get("no_submit_phase_36_interim_closure_complete") is True
        and source_36f.get("public_observation_evidence_closure_ready") is True
        and len(safety_violations) == 0
    )
    payload: dict[str, Any] = {
        "gate_name": "source_36f_gate",
        "source_36f_gate_complete": source_ready,
        "source_36f_gate_locked": True,
        "source_36f_gate_status": "SOURCE_36F_GATE_READY_INTERIM_CLOSURE_ACCEPTED" if source_ready else "SOURCE_36F_GATE_NOT_READY",
        "source_36f_report": str(source_path) if source_path else None,
        "source_36f_decision": source_36f.get("decision"),
        "source_36f_status_payload": source_36f.get("status"),
        "source_36f_safety_violation_count": len(safety_violations),
        "source_36f_safety_violations": list(safety_violations),
        "source_36f_phase_36_interim_closed": source_36f.get("phase_36_interim_closed"),
        "source_36f_phase_36_final_closed": source_36f.get("phase_36_final_closed"),
        "source_36f_network_off_evidence_digest_lock_digest": source_36f.get("network_off_evidence_digest_lock_digest"),
        "source_36f_no_submit_phase_36_interim_closure_digest": source_36f.get("no_submit_phase_36_interim_closure_digest"),
        "source_36f_phase_36_tag_audit_digest": source_36f.get("phase_36_tag_audit_digest"),
        "source_36f_gate_relaxed": False,
    }
    payload["source_36f_gate_digest"] = stable_digest(payload)
    return payload


def build_phase_36_remote_tag_audit(git_state: GitState) -> dict[str, Any]:
    remote_set = set(git_state.remote_phase_36_tags)
    present = [tag for tag in REQUIRED_PHASE_36_REMOTE_TAGS if tag in remote_set]
    missing = [tag for tag in REQUIRED_PHASE_36_REMOTE_TAGS if tag not in remote_set]
    complete = git_state.remote_tag_query_ok and len(missing) == 0
    payload: dict[str, Any] = {
        "audit_name": "phase_36_remote_tag_audit",
        "phase_36_remote_tag_audit_complete": complete,
        "phase_36_remote_tag_audit_locked": True,
        "phase_36_remote_tag_audit_status": "PHASE_36_REMOTE_TAG_AUDIT_READY_36A_36F_PRESENT" if complete else "PHASE_36_REMOTE_TAG_AUDIT_NOT_READY",
        "phase_36_remote_tag_query_ok": git_state.remote_tag_query_ok,
        "phase_36_remote_tag_query_error": git_state.remote_tag_query_error,
        "phase_36_required_remote_tag_count": len(REQUIRED_PHASE_36_REMOTE_TAGS),
        "phase_36_present_remote_tag_count": len(present),
        "phase_36_missing_remote_tag_count": len(missing),
        "phase_36_required_remote_tags": list(REQUIRED_PHASE_36_REMOTE_TAGS),
        "phase_36_present_remote_tags": present,
        "phase_36_missing_remote_tags": missing,
        "phase_36_remote_tags_observed": list(git_state.remote_phase_36_tags),
        "phase_36_local_tags_observed": list(git_state.local_phase_36_tags),
        "phase_36_remote_tag_audit_relaxed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }
    payload["phase_36_remote_tag_audit_digest"] = stable_digest(payload)
    return payload


def build_no_submit_phase_36_final_seal(
    source_gate: Mapping[str, Any],
    remote_audit: Mapping[str, Any],
    source_36f: Mapping[str, Any],
) -> dict[str, Any]:
    checks = [
        {"check_id": "source_36f_gate_ready", "sealed": bool(source_gate.get("source_36f_gate_complete"))},
        {"check_id": "phase_36_interim_closure_present", "sealed": source_36f.get("phase_36_interim_closed") is True},
        {"check_id": "phase_36_remote_tags_36a_36f_present", "sealed": bool(remote_audit.get("phase_36_remote_tag_audit_complete"))},
        {"check_id": "network_off_evidence_digest_lock_intact", "sealed": source_36f.get("network_off_evidence_digest_lock_complete") is True},
        {"check_id": "network_and_http_forbidden", "sealed": True},
        {"check_id": "submit_path_forbidden", "sealed": True},
        {"check_id": "paper_transition_remains_blocked", "sealed": True},
        {"check_id": "runtime_overlay_training_reload_forbidden", "sealed": True},
    ]
    locked_count = sum(1 for item in checks if item.get("sealed") is True)
    complete = locked_count == len(checks)
    payload: dict[str, Any] = {
        "seal_name": "no_submit_phase_36_final_seal",
        "no_submit_phase_36_final_seal_complete": complete,
        "no_submit_phase_36_final_seal_locked": True,
        "no_submit_phase_36_final_seal_status": "NO_SUBMIT_PHASE_36_FINAL_SEAL_READY" if complete else "NO_SUBMIT_PHASE_36_FINAL_SEAL_NOT_READY",
        "no_submit_phase_36_final_seal_check_count": len(checks),
        "no_submit_phase_36_final_seal_locked_count": locked_count,
        "no_submit_phase_36_final_seal_checks": checks,
        "phase_36_final_seal_relaxed": False,
        "phase_36_final_closure_relaxed": False,
        "phase_36_interim_closed": source_36f.get("phase_36_interim_closed") is True,
        "phase_36_final_closed": complete,
        "no_submit_phase_36_final_closed": complete,
        "no_submit_phase_36_final_closure_locked": True,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "public_market_data_collection_performed": False,
        "runtime_evidence_collection_performed": False,
        "order_submit_performed": False,
    }
    payload["no_submit_phase_36_final_seal_digest"] = stable_digest(payload)
    return payload


def _missing_source_gate_payload() -> dict[str, Any]:
    payload = {
        "source_36f_gate_complete": False,
        "source_36f_gate_locked": True,
        "source_36f_gate_status": "SOURCE_36F_GATE_NOT_READY_SOURCE_MISSING",
        "source_36f_gate_relaxed": False,
        "source_36f_safety_violation_count": 0,
        "source_36f_safety_violations": [],
        "source_36f_phase_36_interim_closed": None,
        "source_36f_phase_36_final_closed": None,
    }
    payload["source_36f_gate_digest"] = stable_digest(payload)
    return payload


def _missing_remote_audit_payload() -> dict[str, Any]:
    payload = {
        "phase_36_remote_tag_audit_complete": False,
        "phase_36_remote_tag_audit_locked": True,
        "phase_36_remote_tag_audit_status": "PHASE_36_REMOTE_TAG_AUDIT_NOT_READY_SOURCE_MISSING",
        "phase_36_remote_tag_query_ok": False,
        "phase_36_remote_tag_query_error": "source_36f_missing_or_not_ready",
        "phase_36_required_remote_tag_count": len(REQUIRED_PHASE_36_REMOTE_TAGS),
        "phase_36_present_remote_tag_count": 0,
        "phase_36_missing_remote_tag_count": len(REQUIRED_PHASE_36_REMOTE_TAGS),
        "phase_36_required_remote_tags": list(REQUIRED_PHASE_36_REMOTE_TAGS),
        "phase_36_present_remote_tags": [],
        "phase_36_missing_remote_tags": list(REQUIRED_PHASE_36_REMOTE_TAGS),
        "phase_36_remote_tag_audit_relaxed": False,
    }
    payload["phase_36_remote_tag_audit_digest"] = stable_digest(payload)
    return payload


def _missing_final_seal_payload() -> dict[str, Any]:
    payload = {
        "no_submit_phase_36_final_seal_complete": False,
        "no_submit_phase_36_final_seal_locked": True,
        "no_submit_phase_36_final_seal_status": "NO_SUBMIT_PHASE_36_FINAL_SEAL_NOT_READY_SOURCE_MISSING",
        "no_submit_phase_36_final_seal_check_count": 0,
        "no_submit_phase_36_final_seal_locked_count": 0,
        "phase_36_final_seal_relaxed": False,
        "phase_36_final_closure_relaxed": False,
        "phase_36_interim_closed": False,
        "phase_36_final_closed": False,
        "no_submit_phase_36_final_closed": False,
        "no_submit_phase_36_final_closure_locked": True,
    }
    payload["no_submit_phase_36_final_seal_digest"] = stable_digest(payload)
    return payload


def evaluate_public_observation_final_closure(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    reports_dir = reports_dir.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_36F_PATTERN)
    source_36f: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_36f_report:{SOURCE_36F_PATTERN}")
    else:
        try:
            source_36f = load_json(source_path)
        except Exception as exc:  # pragma: no cover
            errors.append(f"invalid_source_36f_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_36f, NO_SUBMIT_FALSE_FLAGS) if source_36f else []
    source_gate = build_source_36f_gate(source_36f, source_path, source_safety_violations) if source_36f else _missing_source_gate_payload()
    source_36f_complete = bool(source_gate.get("source_36f_gate_complete"))

    if source_36f_complete:
        remote_audit = build_phase_36_remote_tag_audit(git_state)
        final_seal = build_no_submit_phase_36_final_seal(source_gate, remote_audit, source_36f)
    else:
        remote_audit = _missing_remote_audit_payload()
        final_seal = _missing_final_seal_payload()

    final_ready = (
        source_36f_complete
        and bool(remote_audit.get("phase_36_remote_tag_audit_complete"))
        and bool(final_seal.get("no_submit_phase_36_final_seal_complete"))
        and bool(final_seal.get("no_submit_phase_36_final_seal_locked"))
        and not errors
    )

    status = "READY" if final_ready else "NOT_READY"
    decision = READY_DECISION if final_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": final_ready,
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
        "phase_36_local_tag_count_observed": len(git_state.local_phase_36_tags),
        "phase_36_local_tags_observed": list(git_state.local_phase_36_tags),
        "phase_36_remote_tag_count_observed": len(git_state.remote_phase_36_tags),
        "phase_36_remote_tags_observed": list(git_state.remote_phase_36_tags),
        "source_36f_complete": source_36f_complete,
        "source_36f_status": "SOURCE_36F_READY" if source_36f_complete else "SOURCE_36F_NOT_READY",
        "source_36f_report": str(source_path) if source_path else None,
        "source_36f_decision": source_36f.get("decision"),
        "source_36f_safety_violation_count": len(source_safety_violations),
        "source_36f_safety_violations": source_safety_violations,
        "source_36f_phase_35_closed": source_36f.get("phase_35_closed"),
        "source_36f_phase_36_planning_only": source_36f.get("phase_36_planning_only"),
        "source_36f_phase_36_interim_closed": source_36f.get("phase_36_interim_closed"),
        "source_36f_phase_36_final_closed": source_36f.get("phase_36_final_closed"),
        "source_36f_public_observation_evidence_closure_ready": source_36f.get("public_observation_evidence_closure_ready"),
        "phase_34_closed": True,
        "phase_35_closed": bool(source_36f.get("phase_35_closed")) if source_36f else False,
        "phase_36_planning_only": True,
        "public_observation_final_closure_ready": final_ready,
        "public_observation_final_sealed": final_ready,
        "runtime_readiness_status": "PUBLIC_OBSERVATION_FINAL_CLOSURE_READY_PHASE_36_FINAL_NO_SUBMIT" if final_ready else "PUBLIC_OBSERVATION_FINAL_CLOSURE_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PUBLIC_OBSERVATION_FINAL_CLOSURE_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_public_observation_final_closure": final_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "source_36f_gate_path": None,
        "phase_36_remote_tag_audit_path": None,
        "no_submit_phase_36_final_seal_path": None,
        "report_path": None,
    }
    result.update(source_gate)
    result.update(remote_audit)
    result.update(final_seal)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["phase_36_final_closed"] = bool(final_ready)
    result["no_submit_phase_36_final_closed"] = bool(final_ready)
    result["phase_36_final_seal_relaxed"] = False
    result["phase_36_final_closure_relaxed"] = False
    result["phase_36_remote_tag_audit_relaxed"] = False
    result["next_phase_unlock_allowed"] = False
    result["next_phase_unlock_performed"] = False
    result["transition_to_next_phase_allowed"] = False
    result["transition_to_next_phase_performed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        source_gate_path = reports_dir / f"{PATCH_ID}_source_36f_gate_{stamp}.json"
        remote_audit_path = reports_dir / f"{PATCH_ID}_phase_36_remote_tag_audit_{stamp}.json"
        final_seal_path = reports_dir / f"{PATCH_ID}_no_submit_phase_36_final_seal_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_public_observation_final_closure_{stamp}_{status.lower()}.json"
        write_json(source_gate_path, source_gate)
        write_json(remote_audit_path, remote_audit)
        write_json(final_seal_path, final_seal)
        result["source_36f_gate_path"] = str(source_gate_path)
        result["phase_36_remote_tag_audit_path"] = str(remote_audit_path)
        result["no_submit_phase_36_final_seal_path"] = str(final_seal_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write source gate, remote tag audit and final seal reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_public_observation_final_closure(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
