from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436636A"
PATCH_VERSION = "4B.4.3.6.6.36A"
PATCH_NAME = "Post-Phase-35 Runtime Evidence Strategy"
CHECK_NAME = "post_phase_35_runtime_evidence_strategy"
READY_DECISION = "POST_PHASE_35_RUNTIME_EVIDENCE_STRATEGY_READY_NO_SUBMIT_POLICY_BOUNDARY_LOCKED"
NOT_READY_DECISION = "POST_PHASE_35_RUNTIME_EVIDENCE_STRATEGY_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.36B"
SOURCE_35I_PATTERN = "4B436635I_phase_35_final_tag_audit_*_ready.json"

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
    "phase_35_final_closure_relaxed",
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
    "runtime_policy_relaxed",
    "public_data_observation_boundary_relaxed",
    "paper_blocker_reduction_performed",
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
    local_phase_35_tags: tuple[str, ...]


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
        tags_result = _run_git(["tag", "--list", "4B.4.3.6.6.35*"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return GitState(False, None, None, tuple())

    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    tags = tuple(sorted(line.strip() for line in tags_result.stdout.splitlines() if line.strip())) if tags_result.returncode == 0 else tuple()
    return GitState(git_available, branch, head, tags)


def build_runtime_evidence_collection_policy(source_35i: Mapping[str, Any]) -> dict[str, Any]:
    policy_items = [
        {
            "policy_id": "public_market_data_only",
            "control": "Runtime evidence collection may use public market-data endpoints only in a later execution phase.",
            "execution_now": False,
            "private_api_allowed": False,
            "order_submit_allowed": False,
        },
        {
            "policy_id": "no_submit_fail_closed",
            "control": "Any missing source evidence, missing boundary, or unexpected true submit flag keeps collection locked.",
            "execution_now": False,
            "private_api_allowed": False,
            "order_submit_allowed": False,
        },
        {
            "policy_id": "observation_before_paper",
            "control": "Paper transition cannot unlock until runtime evidence quality and sample targets are satisfied.",
            "execution_now": False,
            "paper_unlock_allowed": False,
        },
        {
            "policy_id": "deterministic_evidence_artifacts",
            "control": "Every future collection run must emit immutable JSON evidence with digests and no destructive cleanup.",
            "execution_now": False,
            "archive_or_delete_allowed": False,
        },
        {
            "policy_id": "operator_review_required",
            "control": "Operator review remains mandatory before any paper transition or runtime overlay activation.",
            "execution_now": False,
            "approval_performed": False,
        },
        {
            "policy_id": "runtime_probe_separation",
            "control": "Runtime health probes remain separated from market-data collection until explicitly authorized.",
            "execution_now": False,
            "runtime_probe_performed": False,
        },
    ]
    payload: dict[str, Any] = {
        "policy_name": "runtime_evidence_collection_policy",
        "runtime_evidence_collection_policy_complete": True,
        "runtime_evidence_collection_policy_ready": True,
        "runtime_evidence_collection_policy_item_count": len(policy_items),
        "runtime_evidence_collection_policy_status": "RUNTIME_EVIDENCE_COLLECTION_POLICY_READY_PLANNING_ONLY",
        "runtime_evidence_collection_policy_items": policy_items,
        "source_35i_phase_35_closed": bool(source_35i.get("phase_35_closed")),
        "source_35i_final_closure_digest": source_35i.get("no_submit_phase_35_final_closure_digest"),
        "runtime_policy_relaxed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
    }
    payload["runtime_evidence_collection_policy_digest"] = stable_digest(payload)
    return payload


def build_public_data_observation_boundary(source_35i: Mapping[str, Any]) -> dict[str, Any]:
    boundary_scope = [
        {
            "scope_id": "public_exchange_info_snapshot",
            "source": "public_exchange_metadata",
            "execution_now": False,
            "private_api_required": False,
        },
        {
            "scope_id": "public_klines_observation",
            "source": "public_klines",
            "execution_now": False,
            "private_api_required": False,
        },
        {
            "scope_id": "public_mark_price_observation",
            "source": "public_mark_price",
            "execution_now": False,
            "private_api_required": False,
        },
        {
            "scope_id": "public_book_ticker_observation",
            "source": "public_book_ticker",
            "execution_now": False,
            "private_api_required": False,
        },
        {
            "scope_id": "local_runtime_report_observation",
            "source": "local_reports_only",
            "execution_now": False,
            "private_api_required": False,
        },
    ]
    payload: dict[str, Any] = {
        "boundary_name": "public_data_observation_boundary",
        "public_data_observation_boundary_complete": True,
        "public_data_observation_boundary_locked": True,
        "public_data_observation_boundary_scope_count": len(boundary_scope),
        "public_data_observation_boundary_scope": boundary_scope,
        "public_data_observation_boundary_status": "PUBLIC_DATA_OBSERVATION_BOUNDARY_LOCKED_POLICY_ONLY",
        "public_data_observation_allowed_now": False,
        "public_data_observation_boundary_relaxed": False,
        "public_data_collection_allowed_now": False,
        "public_market_data_collection_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "source_35i_interim_seal_evidence_locked": bool(source_35i.get("interim_seal_evidence_locked")),
    }
    payload["public_data_observation_boundary_digest"] = stable_digest(payload)
    return payload


def build_paper_transition_blocker_reduction_plan(source_35i: Mapping[str, Any]) -> dict[str, Any]:
    blocker_items = [
        {
            "blocker_id": "runtime_evidence_missing",
            "reduction_action": "Define future no-submit public observation evidence package.",
            "resolved_now": False,
            "execution_now": False,
        },
        {
            "blocker_id": "public_data_observation_not_collected",
            "reduction_action": "Keep public data scope frozen before any dry-run execution request.",
            "resolved_now": False,
            "execution_now": False,
        },
        {
            "blocker_id": "runtime_probe_not_authorized",
            "reduction_action": "Maintain separate runtime probe gate before health evidence can count toward readiness.",
            "resolved_now": False,
            "execution_now": False,
        },
        {
            "blocker_id": "operator_paper_transition_token_absent",
            "reduction_action": "Carry paper transition token requirement forward; no simulated approval.",
            "resolved_now": False,
            "execution_now": False,
        },
    ]
    payload: dict[str, Any] = {
        "plan_name": "paper_transition_blocker_reduction_plan",
        "paper_transition_blocker_reduction_plan_complete": True,
        "paper_transition_blocker_reduction_plan_ready": True,
        "paper_transition_blocker_count_carried_forward": len(blocker_items),
        "paper_transition_blocker_reduction_action_count": len(blocker_items),
        "paper_transition_blocker_reduction_items": blocker_items,
        "paper_transition_blocker_reduction_status": "PAPER_TRANSITION_BLOCKER_REDUCTION_PLAN_READY_NO_REDUCTION_PERFORMED",
        "paper_blocker_reduction_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "source_35i_paper_transition_status": source_35i.get("paper_transition_status"),
    }
    payload["paper_transition_blocker_reduction_plan_digest"] = stable_digest(payload)
    return payload


def build_no_submit_strategy_boundary() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "seal_name": "no_submit_phase_36a_strategy_boundary",
        "no_submit_phase_36a_strategy_boundary_complete": True,
        "no_submit_phase_36a_strategy_boundary_locked": True,
        "no_submit_phase_36a_strategy_boundary_status": "NO_SUBMIT_PHASE_36A_STRATEGY_BOUNDARY_LOCKED",
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
    }
    payload["no_submit_phase_36a_strategy_boundary_digest"] = stable_digest(payload)
    return payload


def _build_missing_policy_payload() -> dict[str, Any]:
    return {
        "runtime_evidence_collection_policy_complete": False,
        "runtime_evidence_collection_policy_ready": False,
        "runtime_evidence_collection_policy_status": "RUNTIME_EVIDENCE_COLLECTION_POLICY_NOT_READY_SOURCE_MISSING",
        "runtime_evidence_collection_policy_item_count": 0,
        "runtime_evidence_collection_policy_digest": stable_digest({"missing_source_35i": True}),
        "runtime_policy_relaxed": False,
    }


def _build_missing_boundary_payload() -> dict[str, Any]:
    return {
        "public_data_observation_boundary_complete": False,
        "public_data_observation_boundary_locked": False,
        "public_data_observation_boundary_status": "PUBLIC_DATA_OBSERVATION_BOUNDARY_NOT_READY_SOURCE_MISSING",
        "public_data_observation_boundary_scope_count": 0,
        "public_data_observation_boundary_digest": stable_digest({"missing_source_35i": True}),
        "public_data_observation_allowed_now": False,
        "public_data_observation_boundary_relaxed": False,
    }


def _build_missing_blocker_plan_payload() -> dict[str, Any]:
    return {
        "paper_transition_blocker_reduction_plan_complete": False,
        "paper_transition_blocker_reduction_plan_ready": False,
        "paper_transition_blocker_reduction_status": "PAPER_TRANSITION_BLOCKER_REDUCTION_PLAN_NOT_READY_SOURCE_MISSING",
        "paper_transition_blocker_count_carried_forward": 0,
        "paper_transition_blocker_reduction_action_count": 0,
        "paper_transition_blocker_reduction_plan_digest": stable_digest({"missing_source_35i": True}),
        "paper_blocker_reduction_performed": False,
    }


def evaluate_post_phase_35_runtime_evidence_strategy(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir.resolve()
    repo_root = repo_root.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_35I_PATTERN)
    source_35i: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_35i_report:{SOURCE_35I_PATTERN}")
    else:
        try:
            source_35i = load_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            errors.append(f"invalid_source_35i_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_35i, NO_SUBMIT_FALSE_FLAGS) if source_35i else []
    source_35i_complete = (
        bool(source_35i)
        and source_35i.get("status") == "READY"
        and source_35i.get("decision") == "PHASE_35_FINAL_TAG_AUDIT_READY_NO_SUBMIT_PHASE_35_FINAL_CLOSED"
        and source_35i.get("phase_35_closed") is True
        and source_35i.get("no_submit_phase_35_final_closed") is True
        and source_35i.get("no_submit_phase_35_final_closure_locked") is True
        and int(source_35i.get("phase_35_missing_remote_tag_count", 1)) == 0
        and len(source_safety_violations) == 0
    )

    policy = build_runtime_evidence_collection_policy(source_35i) if source_35i_complete else _build_missing_policy_payload()
    boundary = build_public_data_observation_boundary(source_35i) if source_35i_complete else _build_missing_boundary_payload()
    blocker_plan = build_paper_transition_blocker_reduction_plan(source_35i) if source_35i_complete else _build_missing_blocker_plan_payload()
    no_submit_boundary = build_no_submit_strategy_boundary()

    strategy_ready = (
        source_35i_complete
        and bool(policy.get("runtime_evidence_collection_policy_complete"))
        and bool(boundary.get("public_data_observation_boundary_complete"))
        and bool(boundary.get("public_data_observation_boundary_locked"))
        and bool(blocker_plan.get("paper_transition_blocker_reduction_plan_complete"))
        and bool(no_submit_boundary.get("no_submit_phase_36a_strategy_boundary_locked"))
        and not errors
    )

    status = "READY" if strategy_ready else "NOT_READY"
    decision = READY_DECISION if strategy_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": strategy_ready,
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
        "phase_35_tag_count_observed": len(git_state.local_phase_35_tags),
        "phase_35_tags_observed": list(git_state.local_phase_35_tags),
        "source_35i_complete": source_35i_complete,
        "source_35i_status": "SOURCE_35I_READY" if source_35i_complete else "SOURCE_35I_NOT_READY",
        "source_35i_report": str(source_path) if source_path else None,
        "source_35i_decision": source_35i.get("decision"),
        "source_35i_safety_violation_count": len(source_safety_violations),
        "source_35i_safety_violations": source_safety_violations,
        "source_35i_phase_35_closed": source_35i.get("phase_35_closed"),
        "source_35i_no_submit_phase_35_final_closure_digest": source_35i.get("no_submit_phase_35_final_closure_digest"),
        "source_35i_interim_seal_evidence_lock_digest": source_35i.get("interim_seal_evidence_lock_digest"),
        "source_35i_remote_tag_audit_digest": source_35i.get("phase_35_remote_tag_audit_digest"),
        "phase_34_closed": True,
        "phase_35_closed": bool(source_35i_complete),
        "phase_36_planning_only": True,
        "post_phase_35_runtime_evidence_strategy_ready": strategy_ready,
        "runtime_readiness_status": "POST_PHASE_35_RUNTIME_EVIDENCE_STRATEGY_READY_PLANNING_ONLY_NO_SUBMIT" if strategy_ready else "POST_PHASE_35_RUNTIME_EVIDENCE_STRATEGY_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_POST_PHASE_35_STRATEGY_ONLY_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_post_phase_35_runtime_evidence_strategy": strategy_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "runtime_evidence_collection_policy_path": None,
        "public_data_observation_boundary_path": None,
        "paper_transition_blocker_reduction_plan_path": None,
        "no_submit_phase_36a_strategy_boundary_path": None,
        "report_path": None,
    }
    result.update(policy)
    result.update(boundary)
    result.update(blocker_plan)
    result.update(no_submit_boundary)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["runtime_policy_relaxed"] = False
    result["public_data_observation_boundary_relaxed"] = False
    result["paper_blocker_reduction_performed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        policy_path = reports_dir / f"{PATCH_ID}_runtime_evidence_collection_policy_{stamp}.json"
        boundary_path = reports_dir / f"{PATCH_ID}_public_data_observation_boundary_{stamp}.json"
        blocker_path = reports_dir / f"{PATCH_ID}_paper_transition_blocker_reduction_plan_{stamp}.json"
        no_submit_path = reports_dir / f"{PATCH_ID}_no_submit_phase_36a_strategy_boundary_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_post_phase_35_runtime_evidence_strategy_{stamp}_{status.lower()}.json"
        write_json(policy_path, policy)
        write_json(boundary_path, boundary)
        write_json(blocker_path, blocker_plan)
        write_json(no_submit_path, no_submit_boundary)
        result["runtime_evidence_collection_policy_path"] = str(policy_path)
        result["public_data_observation_boundary_path"] = str(boundary_path)
        result["paper_transition_blocker_reduction_plan_path"] = str(blocker_path)
        result["no_submit_phase_36a_strategy_boundary_path"] = str(no_submit_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write policy, boundary and plan reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_post_phase_35_runtime_evidence_strategy(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
