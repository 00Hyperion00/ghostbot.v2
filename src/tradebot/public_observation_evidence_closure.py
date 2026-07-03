from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436636F"
PATCH_VERSION = "4B.4.3.6.6.36F"
PATCH_NAME = "Public Observation Evidence Closure"
CHECK_NAME = "public_observation_evidence_closure"
READY_DECISION = "PUBLIC_OBSERVATION_EVIDENCE_CLOSURE_READY_NO_SUBMIT_PHASE_36_INTERIM_CLOSED"
NOT_READY_DECISION = "PUBLIC_OBSERVATION_EVIDENCE_CLOSURE_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.36G"
SOURCE_36E_PATTERN = "4B436636E_public_observation_network_off_execution_package_*_ready.json"
REQUIRED_PHASE_36_TAGS: tuple[str, ...] = (
    "4B.4.3.6.6.36A",
    "4B.4.3.6.6.36B",
    "4B.4.3.6.6.36C",
    "4B.4.3.6.6.36D",
    "4B.4.3.6.6.36E",
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
    "network_request_allowed_now",
    "network_request_performed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "no_network_collector_simulation_executed",
    "observation_artifact_written",
    "observation_dry_run_evidence_unsealed",
    "operator_observation_authorization_unlocked",
    "operator_observation_token_consumed",
    "operator_observation_token_validated",
    "order_submit_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "private_account_read_performed",
    "private_api_access_allowed",
    "public_data_fetch_adapter_executed",
    "public_market_data_collection_performed",
    "public_observation_dry_run_collector_executed",
    "public_observation_execution_allowed_now",
    "public_observation_execution_authorized_now",
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
    "phase_36_interim_closure_relaxed",
    "network_off_evidence_digest_lock_relaxed",
    "phase_36_tag_audit_relaxed",
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


def _run_git(args: Sequence[str], cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def read_git_state(repo_root: Path) -> GitState:
    try:
        branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        head_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
        tags_result = _run_git(["tag", "--list", "4B.4.3.6.6.36*"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return GitState(False, None, None, tuple())

    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    tags = tuple(sorted(line.strip() for line in tags_result.stdout.splitlines() if line.strip())) if tags_result.returncode == 0 else tuple()
    return GitState(git_available, branch, head, tags)


def build_phase_36_tag_audit(git_state: GitState) -> dict[str, Any]:
    present = [tag for tag in REQUIRED_PHASE_36_TAGS if tag in set(git_state.local_phase_36_tags)]
    missing = [tag for tag in REQUIRED_PHASE_36_TAGS if tag not in set(git_state.local_phase_36_tags)]
    payload: dict[str, Any] = {
        "audit_name": "phase_36_local_tag_audit",
        "phase_36_tag_audit_complete": len(missing) == 0,
        "phase_36_tag_audit_locked": True,
        "phase_36_tag_audit_status": "PHASE_36_TAG_AUDIT_READY_36A_36E_PRESENT" if not missing else "PHASE_36_TAG_AUDIT_NOT_READY_MISSING_TAGS",
        "phase_36_required_tag_count": len(REQUIRED_PHASE_36_TAGS),
        "phase_36_present_tag_count": len(present),
        "phase_36_missing_tag_count": len(missing),
        "phase_36_required_tags": list(REQUIRED_PHASE_36_TAGS),
        "phase_36_present_tags": present,
        "phase_36_missing_tags": missing,
        "phase_36_tag_audit_relaxed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }
    payload["phase_36_tag_audit_digest"] = stable_digest(payload)
    return payload


def build_network_off_evidence_digest_lock(source_36e: Mapping[str, Any], tag_audit: Mapping[str, Any]) -> dict[str, Any]:
    digest_items = [
        {
            "evidence_id": "token_presence_audit",
            "digest": source_36e.get("token_presence_audit_digest"),
            "locked": True,
        },
        {
            "evidence_id": "no_network_collector_simulation",
            "digest": source_36e.get("no_network_collector_simulation_digest"),
            "locked": True,
        },
        {
            "evidence_id": "observation_execution_dry_run_evidence_seal",
            "digest": source_36e.get("observation_execution_dry_run_evidence_seal_digest"),
            "locked": True,
        },
        {
            "evidence_id": "phase_36_tag_audit",
            "digest": tag_audit.get("phase_36_tag_audit_digest"),
            "locked": True,
        },
    ]
    missing_digest_items = [str(item["evidence_id"]) for item in digest_items if not isinstance(item.get("digest"), str) or not item.get("digest")]
    payload: dict[str, Any] = {
        "lock_name": "network_off_evidence_digest_lock",
        "network_off_evidence_digest_lock_complete": len(missing_digest_items) == 0,
        "network_off_evidence_digest_lock_locked": True,
        "network_off_evidence_digest_lock_status": "NETWORK_OFF_EVIDENCE_DIGEST_LOCK_READY" if not missing_digest_items else "NETWORK_OFF_EVIDENCE_DIGEST_LOCK_NOT_READY_MISSING_DIGESTS",
        "network_off_evidence_digest_item_count": len(digest_items),
        "network_off_evidence_digest_missing_count": len(missing_digest_items),
        "network_off_evidence_digest_missing_items": missing_digest_items,
        "network_off_evidence_digest_items": digest_items,
        "network_off_evidence_digest_lock_relaxed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "public_market_data_collection_performed": False,
        "runtime_evidence_collection_performed": False,
    }
    payload["network_off_evidence_digest_lock_digest"] = stable_digest(payload)
    return payload


def build_no_submit_phase_36_interim_closure(source_36e: Mapping[str, Any], tag_audit: Mapping[str, Any], digest_lock: Mapping[str, Any]) -> dict[str, Any]:
    checks = [
        {"check_id": "source_36e_ready", "sealed": True},
        {"check_id": "phase_36_tags_36a_36e_present", "sealed": bool(tag_audit.get("phase_36_tag_audit_complete"))},
        {"check_id": "network_off_evidence_digests_locked", "sealed": bool(digest_lock.get("network_off_evidence_digest_lock_complete"))},
        {"check_id": "network_forbidden", "sealed": True},
        {"check_id": "market_collection_forbidden", "sealed": True},
        {"check_id": "submit_forbidden", "sealed": True},
        {"check_id": "paper_transition_blocked", "sealed": True},
        {"check_id": "runtime_overlay_forbidden", "sealed": True},
    ]
    locked_count = sum(1 for item in checks if item.get("sealed") is True)
    complete = locked_count == len(checks)
    payload: dict[str, Any] = {
        "closure_name": "no_submit_phase_36_interim_closure",
        "no_submit_phase_36_interim_closure_complete": complete,
        "no_submit_phase_36_interim_closed": complete,
        "no_submit_phase_36_interim_closure_locked": True,
        "no_submit_phase_36_interim_closure_status": "NO_SUBMIT_PHASE_36_INTERIM_CLOSURE_READY" if complete else "NO_SUBMIT_PHASE_36_INTERIM_CLOSURE_NOT_READY",
        "no_submit_phase_36_interim_closure_check_count": len(checks),
        "no_submit_phase_36_interim_closure_locked_count": locked_count,
        "no_submit_phase_36_interim_closure_checks": checks,
        "phase_36_interim_closure_relaxed": False,
        "phase_36_interim_closed": complete,
        "phase_36_final_closed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "source_36e_runtime_readiness_status": source_36e.get("runtime_readiness_status"),
    }
    payload["no_submit_phase_36_interim_closure_digest"] = stable_digest(payload)
    return payload


def _missing_tag_audit_payload() -> dict[str, Any]:
    payload = {
        "phase_36_tag_audit_complete": False,
        "phase_36_tag_audit_locked": True,
        "phase_36_tag_audit_status": "PHASE_36_TAG_AUDIT_NOT_READY_SOURCE_MISSING",
        "phase_36_required_tag_count": len(REQUIRED_PHASE_36_TAGS),
        "phase_36_present_tag_count": 0,
        "phase_36_missing_tag_count": len(REQUIRED_PHASE_36_TAGS),
        "phase_36_required_tags": list(REQUIRED_PHASE_36_TAGS),
        "phase_36_present_tags": [],
        "phase_36_missing_tags": list(REQUIRED_PHASE_36_TAGS),
        "phase_36_tag_audit_relaxed": False,
    }
    payload["phase_36_tag_audit_digest"] = stable_digest(payload)
    return payload


def _missing_digest_lock_payload() -> dict[str, Any]:
    payload = {
        "network_off_evidence_digest_lock_complete": False,
        "network_off_evidence_digest_lock_locked": True,
        "network_off_evidence_digest_lock_status": "NETWORK_OFF_EVIDENCE_DIGEST_LOCK_NOT_READY_SOURCE_MISSING",
        "network_off_evidence_digest_item_count": 0,
        "network_off_evidence_digest_missing_count": 4,
        "network_off_evidence_digest_missing_items": ["source_36e_missing"],
        "network_off_evidence_digest_lock_relaxed": False,
    }
    payload["network_off_evidence_digest_lock_digest"] = stable_digest(payload)
    return payload


def _missing_closure_payload() -> dict[str, Any]:
    payload = {
        "no_submit_phase_36_interim_closure_complete": False,
        "no_submit_phase_36_interim_closed": False,
        "no_submit_phase_36_interim_closure_locked": True,
        "no_submit_phase_36_interim_closure_status": "NO_SUBMIT_PHASE_36_INTERIM_CLOSURE_NOT_READY_SOURCE_MISSING",
        "no_submit_phase_36_interim_closure_check_count": 0,
        "no_submit_phase_36_interim_closure_locked_count": 0,
        "phase_36_interim_closure_relaxed": False,
        "phase_36_interim_closed": False,
        "phase_36_final_closed": False,
    }
    payload["no_submit_phase_36_interim_closure_digest"] = stable_digest(payload)
    return payload


def evaluate_public_observation_evidence_closure(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    reports_dir = reports_dir.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_36E_PATTERN)
    source_36e: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_36e_report:{SOURCE_36E_PATTERN}")
    else:
        try:
            source_36e = load_json(source_path)
        except Exception as exc:  # pragma: no cover
            errors.append(f"invalid_source_36e_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_36e, NO_SUBMIT_FALSE_FLAGS) if source_36e else []
    source_36e_complete = (
        bool(source_36e)
        and source_36e.get("status") == "READY"
        and source_36e.get("decision") == "PUBLIC_OBSERVATION_NETWORK_OFF_EXECUTION_PACKAGE_READY_NO_NETWORK_DRY_RUN_EVIDENCE_SEALED"
        and source_36e.get("source_36d_complete") is True
        and source_36e.get("phase_35_closed") is True
        and source_36e.get("phase_36_planning_only") is True
        and source_36e.get("token_presence_audit_complete") is True
        and source_36e.get("token_presence_audit_locked") is True
        and source_36e.get("no_network_collector_simulation_complete") is True
        and source_36e.get("no_network_collector_simulation_locked") is True
        and source_36e.get("observation_execution_dry_run_evidence_seal_complete") is True
        and source_36e.get("observation_execution_dry_run_evidence_seal_locked") is True
        and source_36e.get("public_observation_network_off_execution_package_ready") is True
        and len(source_safety_violations) == 0
    )

    if source_36e_complete:
        tag_audit = build_phase_36_tag_audit(git_state)
        digest_lock = build_network_off_evidence_digest_lock(source_36e, tag_audit)
        closure = build_no_submit_phase_36_interim_closure(source_36e, tag_audit, digest_lock)
    else:
        tag_audit = _missing_tag_audit_payload()
        digest_lock = _missing_digest_lock_payload()
        closure = _missing_closure_payload()

    closure_ready = (
        source_36e_complete
        and bool(tag_audit.get("phase_36_tag_audit_complete"))
        and bool(digest_lock.get("network_off_evidence_digest_lock_complete"))
        and bool(digest_lock.get("network_off_evidence_digest_lock_locked"))
        and bool(closure.get("no_submit_phase_36_interim_closure_complete"))
        and bool(closure.get("no_submit_phase_36_interim_closure_locked"))
        and not errors
    )

    status = "READY" if closure_ready else "NOT_READY"
    decision = READY_DECISION if closure_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": closure_ready,
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
        "phase_36_tag_count_observed": len(git_state.local_phase_36_tags),
        "phase_36_tags_observed": list(git_state.local_phase_36_tags),
        "source_36e_complete": source_36e_complete,
        "source_36e_status": "SOURCE_36E_READY" if source_36e_complete else "SOURCE_36E_NOT_READY",
        "source_36e_report": str(source_path) if source_path else None,
        "source_36e_decision": source_36e.get("decision"),
        "source_36e_safety_violation_count": len(source_safety_violations),
        "source_36e_safety_violations": source_safety_violations,
        "source_36e_phase_35_closed": source_36e.get("phase_35_closed"),
        "source_36e_phase_36_planning_only": source_36e.get("phase_36_planning_only"),
        "source_36e_token_presence_audit_digest": source_36e.get("token_presence_audit_digest"),
        "source_36e_no_network_collector_simulation_digest": source_36e.get("no_network_collector_simulation_digest"),
        "source_36e_observation_execution_dry_run_evidence_seal_digest": source_36e.get("observation_execution_dry_run_evidence_seal_digest"),
        "phase_34_closed": True,
        "phase_35_closed": bool(source_36e.get("phase_35_closed")) if source_36e else False,
        "phase_36_planning_only": True,
        "public_observation_evidence_closure_ready": closure_ready,
        "runtime_readiness_status": "PUBLIC_OBSERVATION_EVIDENCE_CLOSURE_READY_PHASE_36_INTERIM_NO_SUBMIT" if closure_ready else "PUBLIC_OBSERVATION_EVIDENCE_CLOSURE_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PUBLIC_OBSERVATION_EVIDENCE_CLOSURE_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_public_observation_evidence_closure": closure_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "phase_36_tag_audit_path": None,
        "network_off_evidence_digest_lock_path": None,
        "no_submit_phase_36_interim_closure_path": None,
        "report_path": None,
    }
    result.update(tag_audit)
    result.update(digest_lock)
    result.update(closure)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["phase_36_final_closed"] = False
    result["phase_36_interim_closed"] = bool(closure_ready)
    result["network_off_evidence_digest_lock_relaxed"] = False
    result["phase_36_tag_audit_relaxed"] = False
    result["phase_36_interim_closure_relaxed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        tag_audit_path = reports_dir / f"{PATCH_ID}_phase_36_tag_audit_{stamp}.json"
        digest_lock_path = reports_dir / f"{PATCH_ID}_network_off_evidence_digest_lock_{stamp}.json"
        interim_closure_path = reports_dir / f"{PATCH_ID}_no_submit_phase_36_interim_closure_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_public_observation_evidence_closure_{stamp}_{status.lower()}.json"
        write_json(tag_audit_path, tag_audit)
        write_json(digest_lock_path, digest_lock)
        write_json(interim_closure_path, closure)
        result["phase_36_tag_audit_path"] = str(tag_audit_path)
        result["network_off_evidence_digest_lock_path"] = str(digest_lock_path)
        result["no_submit_phase_36_interim_closure_path"] = str(interim_closure_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write tag audit, digest lock and interim closure reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_public_observation_evidence_closure(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
