from __future__ import annotations

import datetime as _dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

PATCH_ID = "4B436634I"
PATCH_VERSION = "4B.4.3.6.6.34I"
PATCH_NAME = "Post-Closure Tag Audit"
READY_DECISION = "POST_CLOSURE_TAG_AUDIT_READY_NO_SUBMIT_PHASE_34_FINAL_SEALED"
NOT_READY_DECISION = "POST_CLOSURE_TAG_AUDIT_NOT_READY"
SOURCE_READY_DECISION = "SIGNATURE_PACKAGE_CLOSURE_READY_NO_SUBMIT_CHAIN_CLOSED"
NEXT_PHASE = "4B.4.3.6.6.35A"

REQUIRED_PHASE_34_TAGS: tuple[str, ...] = tuple(
    f"4B.4.3.6.6.34{suffix}" for suffix in "ABCDEFGH"
)

FALSE_SAFETY_KEYS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
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
    "archive_execution_allowed",
    "archive_move_performed",
    "file_delete_performed",
    "file_move_performed",
    "report_delete_performed",
    "destructive_cleanup_performed",
    "deduplication_action_performed",
    "approval_performed",
    "simulated_approval_performed",
    "submit_boundary_relaxed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
)

EXPECTED_34I_SELF_ARTIFACTS: tuple[str, ...] = (
    "README_APPLY_4B436634I.txt",
    "docs/POST_CLOSURE_TAG_AUDIT_4B436634I.md",
    "src/tradebot/post_closure_tag_audit.py",
    "tests/test_post_closure_tag_audit_4B436634I.py",
    "tools/apply_4B436634I_post_closure_tag_audit.py",
    "tools/check_4B436634I_post_closure_tag_audit.py",
    "tools/run_4B436634I_post_closure_tag_audit.py",
    "tools/rollback_4B436634I_post_closure_tag_audit.py",
)

EXPECTED_34I_PREFIXES: tuple[str, ...] = (
    "reports/recovery/4B436634I_",
    "tools/_patch_backup_4B436634I_",
)


def _utc_timestamp() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _nested_get(payload: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in payload:
        return payload[key]
    for container_key in (
        "safety_snapshot",
        "acceptance",
        "tag_audit",
        "closure",
        "governance",
        "source",
        "decision_snapshot",
    ):
        container = payload.get(container_key)
        if isinstance(container, dict) and key in container:
            return container[key]
    return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = sorted(
        reports_dir.glob("4B436634H_signature_package_closure_*_ready.json"),
        key=lambda p: (p.stat().st_mtime, p.name),
        reverse=True,
    )
    return candidates[0] if candidates else None


def _run_git(repo_root: Path, args: list[str], timeout_seconds: int = 8) -> tuple[bool, str, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, "", str(exc)
    return completed.returncode == 0, completed.stdout.strip(), completed.stderr.strip()


def _git_snapshot(repo_root: Path) -> dict[str, Any]:
    available, inside, inside_err = _run_git(repo_root, ["rev-parse", "--is-inside-work-tree"])
    git_available = available and inside.strip().lower() == "true"
    snapshot: dict[str, Any] = {
        "git_available": git_available,
        "git_error": "" if git_available else inside_err,
        "git_branch": None,
        "git_head_short": None,
        "local_tags": [],
        "phase_34h_tag_commit": None,
        "raw_git_status_lines": [],
    }
    if not git_available:
        return snapshot

    ok_branch, branch, _ = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    ok_head, head, _ = _run_git(repo_root, ["rev-parse", "--short", "HEAD"])
    ok_tags, tags, _ = _run_git(repo_root, ["tag", "--list", "4B.4.3.6.6.34*"])
    ok_status, status, _ = _run_git(repo_root, ["status", "--short"])
    ok_34h_commit, tag_commit, _ = _run_git(repo_root, ["rev-list", "-n", "1", "4B.4.3.6.6.34H"])

    snapshot["git_branch"] = branch if ok_branch else None
    snapshot["git_head_short"] = head if ok_head else None
    snapshot["local_tags"] = sorted(line.strip() for line in tags.splitlines() if line.strip()) if ok_tags else []
    snapshot["raw_git_status_lines"] = [line.rstrip() for line in status.splitlines() if line.strip()] if ok_status else []
    snapshot["phase_34h_tag_commit"] = tag_commit if ok_34h_commit else None
    return snapshot


def _extract_dirty_path(status_line: str) -> str:
    raw = status_line[3:] if len(status_line) > 3 else status_line
    raw = raw.strip().strip('"')
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1].strip().strip('"')
    return raw.replace("\\", "/")


def _is_expected_34i_artifact(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/")
    if normalized in EXPECTED_34I_SELF_ARTIFACTS:
        return True
    if any(normalized.startswith(prefix) for prefix in EXPECTED_34I_PREFIXES):
        return True
    # Git may collapse a fully untracked tree as `?? src/` or `?? docs/`.
    # Treat that as expected only when it is a parent directory of a known 34I artifact.
    if normalized.endswith("/"):
        return any(expected.startswith(normalized) for expected in EXPECTED_34I_SELF_ARTIFACTS)
    return False


def _clean_worktree_confirmation(git_snapshot: dict[str, Any]) -> dict[str, Any]:
    raw_lines = list(git_snapshot.get("raw_git_status_lines") or [])
    dirty_paths = [_extract_dirty_path(line) for line in raw_lines]
    ignored_paths = [path for path in dirty_paths if _is_expected_34i_artifact(path)]
    blocking_paths = [path for path in dirty_paths if not _is_expected_34i_artifact(path)]
    normalized_dirty_count = len(blocking_paths)
    raw_dirty_count = len(dirty_paths)
    complete = bool(git_snapshot.get("git_available")) and normalized_dirty_count == 0
    if raw_dirty_count == 0:
        status = "WORKTREE_CLEAN"
    elif complete:
        status = "WORKTREE_CLEAN_EXCEPT_34I_SELF_ARTIFACTS"
    else:
        status = "WORKTREE_DIRTY_BLOCKING_NON_34I_ARTIFACTS"
    return {
        "clean_worktree_confirmation_complete": complete,
        "clean_worktree_status": status,
        "raw_dirty_worktree_count": raw_dirty_count,
        "normalized_dirty_worktree_count": normalized_dirty_count,
        "ignored_34i_self_artifact_count": len(ignored_paths),
        "dirty_worktree_blocker_count": normalized_dirty_count,
        "dirty_worktree_advisory_only": True,
        "dirty_worktree_blockers": blocking_paths,
        "ignored_34i_self_artifacts": ignored_paths,
    }


def _source_34h_state(source_report: Path | None) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    if source_report is None:
        return False, {}, {
            "source_34h_complete": False,
            "source_34h_report": None,
            "source_34h_decision": None,
            "source_34h_status": "SOURCE_34H_REPORT_NOT_FOUND",
        }
    try:
        payload = _read_json(source_report)
    except Exception as exc:  # pragma: no cover - defensive IO path
        return False, {}, {
            "source_34h_complete": False,
            "source_34h_report": str(source_report).replace("\\", "/"),
            "source_34h_decision": None,
            "source_34h_status": f"SOURCE_34H_REPORT_UNREADABLE:{exc}",
        }

    safety_violations = [key for key in FALSE_SAFETY_KEYS if _as_bool(_nested_get(payload, key, False))]
    source_decision = _nested_get(payload, "decision")
    source_status = _nested_get(payload, "status")
    complete = (
        source_status == "READY"
        and source_decision == SOURCE_READY_DECISION
        and _as_bool(_nested_get(payload, "source_34g_complete", False))
        and _as_bool(_nested_get(payload, "accepted_for_governance_closure", False))
        and _as_bool(_nested_get(payload, "final_governance_acceptance_complete", False))
        and _as_bool(_nested_get(payload, "no_submit_chain_closure_complete", False))
        and _as_bool(_nested_get(payload, "no_submit_chain_closed", False))
        and _as_bool(_nested_get(payload, "phase_34_tag_audit_complete", False))
        and _as_bool(_nested_get(payload, "governance_locked", False))
        and not safety_violations
    )
    state = {
        "source_34h_complete": complete,
        "source_34h_report": str(source_report).replace("\\", "/"),
        "source_34h_decision": source_decision,
        "source_34h_status": "SOURCE_34H_READY" if complete else "SOURCE_34H_NOT_READY_OR_UNSAFE",
        "source_34h_safety_violation_count": len(safety_violations),
        "source_34h_safety_violations": safety_violations,
        "baseline_digest": _nested_get(payload, "baseline_digest"),
        "evidence_review_digest": _nested_get(payload, "evidence_review_digest"),
        "eligibility_matrix_freeze_digest": _nested_get(payload, "eligibility_matrix_freeze_digest"),
        "final_no_submit_governance_digest": _nested_get(payload, "final_no_submit_governance_digest"),
        "no_submit_approval_digest": _nested_get(payload, "no_submit_approval_digest"),
        "no_submit_handoff_digest": _nested_get(payload, "no_submit_handoff_digest"),
        "manifest_sha256": _nested_get(payload, "manifest_sha256"),
        "immutable_plan_digest": _nested_get(payload, "immutable_plan_digest"),
    }
    return complete, payload, state


def _tag_verification(git_snapshot: dict[str, Any]) -> dict[str, Any]:
    local_tags = set(git_snapshot.get("local_tags") or [])
    missing = [tag for tag in REQUIRED_PHASE_34_TAGS if tag not in local_tags]
    present = [tag for tag in REQUIRED_PHASE_34_TAGS if tag in local_tags]
    complete = bool(git_snapshot.get("git_available")) and not missing
    ledger = {
        "phase_34h_tag_verification_complete": complete,
        "phase_34_tag_verification_status": "PHASE_34H_TAG_VERIFIED" if complete else "PHASE_34_TAG_VERIFICATION_NOT_READY",
        "required_tag_count": len(REQUIRED_PHASE_34_TAGS),
        "present_tag_count": len(present),
        "missing_tag_count": len(missing),
        "required_tags": list(REQUIRED_PHASE_34_TAGS),
        "present_tags": present,
        "missing_tags": missing,
        "phase_34h_tag_present": "4B.4.3.6.6.34H" in local_tags,
        "phase_34h_tag_commit": git_snapshot.get("phase_34h_tag_commit"),
        "git_branch": git_snapshot.get("git_branch"),
        "git_head_short": git_snapshot.get("git_head_short"),
    }
    ledger["phase_34h_tag_verification_digest"] = _json_digest({
        "required_tags": ledger["required_tags"],
        "present_tags": ledger["present_tags"],
        "missing_tags": ledger["missing_tags"],
        "phase_34h_tag_commit": ledger["phase_34h_tag_commit"],
    })
    return ledger


def evaluate_post_closure_tag_audit(
    *,
    repo_root: str | Path = ".",
    reports_dir: str | Path = "reports/recovery",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    reports_path = (root / reports_dir).resolve() if not Path(reports_dir).is_absolute() else Path(reports_dir).resolve()
    source_report = _find_latest_source_report(reports_path)
    source_complete, _source_payload, source_state = _source_34h_state(source_report)
    git_snapshot = _git_snapshot(root)
    tag_state = _tag_verification(git_snapshot)
    worktree_state = _clean_worktree_confirmation(git_snapshot)

    seal_basis = {
        "source_34h_complete": source_complete,
        "phase_34h_tag_verification_complete": tag_state["phase_34h_tag_verification_complete"],
        "clean_worktree_confirmation_complete": worktree_state["clean_worktree_confirmation_complete"],
        "governance_locked": True,
        "submit_boundary_locked": True,
        "exchange_submit_not_approved": True,
        "live_real_not_approved": True,
    }
    final_seal_complete = all(bool(value) for value in seal_basis.values())
    seal_state = {
        "no_submit_phase_34_final_seal_complete": final_seal_complete,
        "no_submit_phase_34_final_sealed": final_seal_complete,
        "phase_34_closed": final_seal_complete,
        "accepted_for_phase_34_final_seal": final_seal_complete,
        "phase_34_final_seal_status": "NO_SUBMIT_PHASE_34_FINAL_SEALED" if final_seal_complete else "NO_SUBMIT_PHASE_34_FINAL_SEAL_NOT_READY",
        "phase_34_final_seal_digest": _json_digest(seal_basis),
    }

    ready = bool(final_seal_complete)
    result: dict[str, Any] = {
        "ok": ready,
        "status": "READY" if ready else "NOT_READY",
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "check_name": "post_closure_tag_audit",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "next_phase": NEXT_PHASE,
        **source_state,
        **tag_state,
        **worktree_state,
        **seal_state,
        "git_available": git_snapshot.get("git_available"),
        "git_branch": git_snapshot.get("git_branch"),
        "git_head_short": git_snapshot.get("git_head_short"),
        "governance_locked": True,
        "real_operator_signature_present": False,
        "approval_performed": False,
        "simulated_approval_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "submit_boundary_relaxed": False,
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
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "destructive_cleanup_performed": False,
        "deduplication_action_performed": False,
        "phase_34h_tag_verification_path": None,
        "clean_worktree_confirmation_path": None,
        "no_submit_phase_34_final_seal_path": None,
        "report_path": None,
    }
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(path).replace("\\", "/")


def run_post_closure_tag_audit(
    *,
    repo_root: str | Path = ".",
    reports_dir: str | Path = "reports/recovery",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    reports_path = (root / reports_dir).resolve() if not Path(reports_dir).is_absolute() else Path(reports_dir).resolve()
    result = evaluate_post_closure_tag_audit(repo_root=root, reports_dir=reports_path)
    ts = _utc_timestamp()

    tag_ledger = {
        key: result.get(key)
        for key in (
            "patch_id",
            "patch_version",
            "phase_34h_tag_verification_complete",
            "phase_34_tag_verification_status",
            "required_tag_count",
            "present_tag_count",
            "missing_tag_count",
            "required_tags",
            "present_tags",
            "missing_tags",
            "phase_34h_tag_present",
            "phase_34h_tag_commit",
            "git_branch",
            "git_head_short",
            "phase_34h_tag_verification_digest",
        )
    }
    worktree_ledger = {
        key: result.get(key)
        for key in (
            "patch_id",
            "patch_version",
            "clean_worktree_confirmation_complete",
            "clean_worktree_status",
            "raw_dirty_worktree_count",
            "normalized_dirty_worktree_count",
            "ignored_34i_self_artifact_count",
            "dirty_worktree_blocker_count",
            "dirty_worktree_advisory_only",
            "dirty_worktree_blockers",
            "ignored_34i_self_artifacts",
            "git_branch",
            "git_head_short",
        )
    }
    final_seal_ledger = {
        key: result.get(key)
        for key in (
            "patch_id",
            "patch_version",
            "source_34h_complete",
            "phase_34h_tag_verification_complete",
            "clean_worktree_confirmation_complete",
            "no_submit_phase_34_final_seal_complete",
            "no_submit_phase_34_final_sealed",
            "phase_34_closed",
            "accepted_for_phase_34_final_seal",
            "phase_34_final_seal_status",
            "phase_34_final_seal_digest",
            "governance_locked",
            "approved_for_exchange_submit",
            "approved_for_live_real",
            "exchange_submit_allowed",
            "network_submit_allowed",
            "order_submit_performed",
            "next_phase_unlock_allowed",
            "next_phase_unlock_performed",
        )
    }

    tag_path = _write_json(reports_path / f"{PATCH_ID}_34h_tag_verification_{ts}.json", tag_ledger)
    worktree_path = _write_json(reports_path / f"{PATCH_ID}_clean_worktree_confirmation_{ts}.json", worktree_ledger)
    final_seal_path = _write_json(reports_path / f"{PATCH_ID}_no_submit_phase_34_final_seal_{ts}.json", final_seal_ledger)
    suffix = "ready" if result["status"] == "READY" else "not_ready"
    report_path = _write_json(reports_path / f"{PATCH_ID}_post_closure_tag_audit_{ts}_{suffix}.json", result | {
        "phase_34h_tag_verification_path": tag_path,
        "clean_worktree_confirmation_path": worktree_path,
        "no_submit_phase_34_final_seal_path": final_seal_path,
    })

    result["phase_34h_tag_verification_path"] = tag_path
    result["clean_worktree_confirmation_path"] = worktree_path
    result["no_submit_phase_34_final_seal_path"] = final_seal_path
    result["report_path"] = report_path
    return result
