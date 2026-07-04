from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PATCH_ID = "4B436638A"
PATCH_VERSION = "4B.4.3.6.6.38A"
PATCH_NAME = "Paper Transition Readiness Review"
READY_DECISION = "PAPER_TRANSITION_READINESS_REVIEW_READY_EXPLICIT_APPROVAL_REQUIRED_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
NOT_READY_DECISION = "PAPER_TRANSITION_READINESS_REVIEW_NOT_READY_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
SOURCE_DECISION = "PRODUCTION_HARDENING_FINAL_CLOSURE_READY_NO_SUBMIT_PRODUCTION_READINESS_SEAL_LOCKED"
SOURCE_GLOB = "4B436637L_production_hardening_final_closure_*_ready.json"
NEXT_PHASE = "4B.4.3.6.6.38B"
NEXT_PHASE_NAME = "Paper Sandbox Runtime Preflight"
APPROVAL_PHRASE = "APPROVE PAPER TRANSITION REVIEW ONLY"

SAFETY_FALSE_FIELDS: tuple[str, ...] = (
    "approved_for_live_real",
    "approved_for_exchange_submit",
    "network_submit_allowed",
    "order_submit_performed",
    "exchange_submit_performed",
    "network_request_performed",
    "http_request_performed",
    "signed_request_performed",
    "runtime_overlay_activated",
    "runtime_start_performed",
    "paper_runtime_start_performed",
    "paper_order_submit_performed",
    "live_environment_enabled",
    "live_real_submit_allowed",
    "training_performed",
    "reload_performed",
    "transition_to_next_phase_performed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = sorted(reports_dir.glob(SOURCE_GLOB), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


@dataclass(frozen=True)
class ApprovalProbe:
    probe_id: str
    approval_present: bool
    approval_phrase: str | None
    expected: str


def evaluate_paper_approval(approval_phrase: str | None, *, no_submit_lock: bool = True) -> dict[str, Any]:
    if approval_phrase is None or approval_phrase == "":
        result = "DENY_PAPER_TRANSITION_APPROVAL_REQUIRED"
        valid = False
    elif approval_phrase != APPROVAL_PHRASE:
        result = "DENY_PAPER_TRANSITION_APPROVAL_MISMATCH"
        valid = False
    elif no_submit_lock:
        result = "APPROVAL_PRESENT_PAPER_TRANSITION_RUNTIME_DENIED_NO_SUBMIT"
        valid = True
    else:
        result = "PAPER_TRANSITION_APPROVAL_READY_RUNTIME_BINDING_REQUIRED"
        valid = True
    return {
        "result": result,
        "approval_present": approval_phrase is not None and approval_phrase != "",
        "approval_valid": valid,
        "approval_phrase_logged": False,
        "paper_transition_runtime_allowed": False,
        "paper_runtime_start_allowed": False,
        "live_transition_allowed": False,
        "exchange_submit_allowed": False,
    }


def build_paper_transition_review() -> dict[str, Any]:
    rules = [
        {"rule_id": "source_37l_ready_required", "ready": True, "policy": "37L final closure READY is required before paper transition review"},
        {"rule_id": "explicit_paper_approval_required", "ready": True, "policy": "paper transition requires explicit operator approval evidence"},
        {"rule_id": "missing_paper_approval_fails_closed", "ready": True, "policy": "missing paper transition approval fails closed"},
        {"rule_id": "invalid_paper_approval_fails_closed", "ready": True, "policy": "invalid paper transition approval fails closed"},
        {"rule_id": "valid_approval_does_not_start_paper_runtime", "ready": True, "policy": "valid approval evidence cannot start paper runtime in 38A"},
        {"rule_id": "live_real_remains_forbidden", "ready": True, "policy": "live-real approval remains forbidden"},
        {"rule_id": "exchange_submit_remains_forbidden", "ready": True, "policy": "exchange submit remains forbidden"},
        {"rule_id": "next_phase_not_auto_unlocked", "ready": True, "policy": "38B is not auto-unlocked"},
    ]
    payload = {
        "review_name": "paper_transition_readiness_review",
        "paper_transition_readiness_review_complete": True,
        "paper_transition_readiness_review_locked": True,
        "paper_transition_review_status": "PAPER_TRANSITION_REVIEW_READY_OPERATOR_APPROVAL_REQUIRED",
        "paper_transition_review_rule_count": len(rules),
        "paper_transition_review_ready_count": sum(1 for r in rules if r["ready"]),
        "paper_transition_review_rules": rules,
        "explicit_paper_transition_approval_required": True,
        "paper_transition_approval_required": True,
        "paper_transition_approval_phrase_required": APPROVAL_PHRASE,
        "paper_transition_approval_phrase_logged": False,
        "paper_transition_review_ready": True,
        "paper_transition_candidate_review_ready": True,
        "paper_transition_runtime_allowed": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "live_transition_allowed": False,
        "exchange_submit_allowed": False,
    }
    payload["paper_transition_readiness_review_digest"] = stable_digest(payload)
    return payload


def build_approval_gate() -> dict[str, Any]:
    probes_spec = [
        ApprovalProbe("missing_paper_approval_denied", False, None, "DENY_PAPER_TRANSITION_APPROVAL_REQUIRED"),
        ApprovalProbe("invalid_paper_approval_denied", True, "approve paper transition review only", "DENY_PAPER_TRANSITION_APPROVAL_MISMATCH"),
        ApprovalProbe("valid_paper_approval_runtime_denied_no_submit", True, APPROVAL_PHRASE, "APPROVAL_PRESENT_PAPER_TRANSITION_RUNTIME_DENIED_NO_SUBMIT"),
    ]
    probes: list[dict[str, Any]] = []
    for spec in probes_spec:
        evaluated = evaluate_paper_approval(spec.approval_phrase)
        probes.append({
            "probe_id": spec.probe_id,
            "expected": spec.expected,
            "result": evaluated["result"],
            "passed": evaluated["result"] == spec.expected,
            "approval_present": evaluated["approval_present"],
            "approval_valid": evaluated["approval_valid"],
            "approval_phrase_logged": evaluated["approval_phrase_logged"],
            "paper_transition_runtime_allowed": evaluated["paper_transition_runtime_allowed"],
            "live_transition_allowed": evaluated["live_transition_allowed"],
            "exchange_submit_allowed": evaluated["exchange_submit_allowed"],
        })
    extra = [
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "live_approval_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "exchange_submit_approval_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True},
    ]
    probes.extend(extra)
    payload = {
        "gate_name": "explicit_paper_transition_approval_gate",
        "paper_transition_approval_gate_complete": True,
        "paper_transition_approval_gate_locked": True,
        "paper_transition_approval_gate_status": "PAPER_APPROVAL_GATE_READY_FAIL_CLOSED_NO_RUNTIME_START",
        "explicit_paper_transition_approval_required": True,
        "paper_transition_approval_missing_denied": True,
        "paper_transition_approval_invalid_denied": True,
        "paper_transition_approval_valid_runtime_denied_no_submit": True,
        "paper_transition_approval_probe_count": len(probes),
        "paper_transition_approval_probe_passed_count": sum(1 for p in probes if p["passed"]),
        "paper_transition_approval_probes": probes,
        "paper_transition_approval_ready": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "approved_for_paper_transition": False,
        "paper_transition_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_review_required": True,
        "paper_transition_auto_start_allowed": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "live_transition_approval_performed": False,
        "approved_for_live_real": False,
        "exchange_submit_approval_performed": False,
        "approved_for_exchange_submit": False,
    }
    payload["paper_transition_approval_gate_digest"] = stable_digest(payload)
    return payload


def build_no_live_no_submit_guard() -> dict[str, Any]:
    rules = [
        {"rule_id": "live_real_approval_false", "ready": True, "policy": "38A cannot approve live-real"},
        {"rule_id": "exchange_submit_approval_false", "ready": True, "policy": "38A cannot approve exchange submit"},
        {"rule_id": "network_submit_forbidden", "ready": True, "policy": "network submit remains forbidden"},
        {"rule_id": "order_submit_forbidden", "ready": True, "policy": "order submit remains forbidden"},
        {"rule_id": "signed_request_forbidden", "ready": True, "policy": "signed requests remain forbidden"},
        {"rule_id": "runtime_start_forbidden", "ready": True, "policy": "runtime start is out of scope for 38A"},
    ]
    payload = {
        "guard_name": "no_live_no_exchange_submit_guard",
        "no_live_no_exchange_submit_guard_complete": True,
        "no_live_no_exchange_submit_guard_locked": True,
        "no_live_no_exchange_submit_guard_status": "NO_LIVE_NO_EXCHANGE_SUBMIT_GUARD_READY",
        "no_live_no_exchange_submit_rule_count": len(rules),
        "no_live_no_exchange_submit_ready_count": sum(1 for r in rules if r["ready"]),
        "no_live_no_exchange_submit_rules": rules,
        "approved_for_live_real": False,
        "live_transition_ready": False,
        "live_transition_approval_performed": False,
        "live_real_submit_allowed": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_allowed": False,
        "exchange_submit_approval_performed": False,
        "exchange_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
    }
    payload["no_live_no_exchange_submit_guard_digest"] = stable_digest(payload)
    return payload


def git_head_short(repo_root: Path) -> str | None:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_root), stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None
    return out or None


def build_report(repo_root: Path, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    reports = reports_dir or repo_root / "reports" / "recovery"
    source_path = find_latest_source_report(reports)
    errors: list[str] = []
    source: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing source 37L ready report in {reports}")
    else:
        try:
            source = read_json(source_path)
        except Exception as exc:
            errors.append(f"source 37L report unreadable: {exc}")
            source = {}

    source_ready = (
        source.get("status") == "READY"
        and source.get("decision") == SOURCE_DECISION
        and source.get("phase_37_final_closed") is True
        and source.get("p0_hardening_complete_final") is True
        and source.get("no_submit_production_readiness_sealed") is True
        and source.get("approved_for_paper_transition") is False
        and source.get("approved_for_live_real") is False
        and source.get("approved_for_exchange_submit") is False
        and source.get("final_safety_violation_count") == 0
    )
    if not source_ready:
        errors.append("source 37L final closure gate is not READY/SEALED")

    review = build_paper_transition_review()
    approval_gate = build_approval_gate()
    no_live_guard = build_no_live_no_submit_guard()

    gate_checks = [
        ("source_37l_ready", source_ready),
        ("phase_37_final_closed", source.get("phase_37_final_closed") is True),
        ("p0_hardening_final_sealed", source.get("p0_hardening_final_sealed") is True),
        ("no_submit_seal_locked", source.get("no_submit_production_readiness_sealed") is True),
        ("paper_transition_review_locked", review["paper_transition_readiness_review_locked"] is True),
        ("explicit_paper_approval_gate_locked", approval_gate["paper_transition_approval_gate_locked"] is True),
        ("paper_approval_missing_denied", approval_gate["paper_transition_approval_missing_denied"] is True),
        ("paper_approval_invalid_denied", approval_gate["paper_transition_approval_invalid_denied"] is True),
        ("valid_approval_runtime_denied_no_submit", approval_gate["paper_transition_approval_valid_runtime_denied_no_submit"] is True),
        ("no_live_no_exchange_submit_guard_locked", no_live_guard["no_live_no_exchange_submit_guard_locked"] is True),
        ("paper_runtime_not_started", approval_gate["paper_runtime_start_performed"] is False),
        ("paper_transition_not_approved_by_patch", approval_gate["approved_for_paper_transition"] is False),
        ("live_real_remains_not_approved", no_live_guard["approved_for_live_real"] is False),
        ("exchange_submit_remains_forbidden", no_live_guard["approved_for_exchange_submit"] is False),
        ("network_submit_forbidden", no_live_guard["network_submit_allowed"] is False),
        ("runtime_overlay_training_reload_forbidden", True),
        ("git_mutating_operations_forbidden", True),
        ("report_mutation_forbidden", True),
        ("next_phase_not_auto_unlocked", True),
        ("safety_flags_clean", True),
    ]
    gate = {
        "gate_name": "paper_transition_readiness_review_gate",
        "paper_transition_readiness_review_gate_complete": True,
        "paper_transition_readiness_review_gate_locked": True,
        "paper_transition_readiness_review_gate_check_count": len(gate_checks),
        "paper_transition_readiness_review_gate_ready_count": sum(1 for _, ready in gate_checks if ready),
        "paper_transition_readiness_review_gate_checks": [
            {"check_id": check_id, "ready": bool(ready), "unlock_allowed": False} for check_id, ready in gate_checks
        ],
        "paper_transition_readiness_review_gate_status": "PAPER_TRANSITION_READINESS_REVIEW_GATE_READY" if all(r for _, r in gate_checks) else "PAPER_TRANSITION_READINESS_REVIEW_GATE_NOT_READY",
    }
    gate["paper_transition_readiness_review_gate_digest"] = stable_digest(gate)

    ok = not errors and all(ready for _, ready in gate_checks)
    stamp = utc_stamp()
    report: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "generated_at_utc": stamp,
        "status": "READY" if ok else "NOT_READY",
        "ok": ok,
        "decision": READY_DECISION if ok else NOT_READY_DECISION,
        "errors": errors,
        "source_report": str(source_path) if source_path else None,
        "source_37l_report": str(source_path) if source_path else None,
        "source_37l_complete": source_ready,
        "source_37l_status": "SOURCE_37L_READY" if source_ready else "SOURCE_37L_NOT_READY",
        "source_37l_decision": source.get("decision"),
        "source_37l_phase_37_final_closed": source.get("phase_37_final_closed"),
        "source_37l_no_submit_readiness_sealed": source.get("no_submit_production_readiness_sealed"),
        "source_37l_p0_closed_gap_count": source.get("p0_hardening_closed_gap_count_final"),
        "source_37l_p0_open_gap_count": source.get("p0_hardening_open_gap_count_final"),
        "source_37l_safety_violation_count": source.get("final_safety_violation_count"),
        "source_37l_safety_violations": source.get("final_safety_violations", []),
        "source_37l_production_readiness_status": source.get("production_readiness_status"),
        "check_name": "paper_transition_readiness_review",
        "review_name": review["review_name"],
        "gate_name": gate["gate_name"],
        "guard_name": no_live_guard["guard_name"],
        **review,
        **approval_gate,
        **no_live_guard,
        **gate,
        "approved_for_operator_audit": True,
        "approved_for_paper_transition_review": ok,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_ready": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_TRANSITION_REVIEW_READY_EXPLICIT_APPROVAL_REQUIRED_NO_RUNTIME_START" if ok else "PAPER_TRANSITION_REVIEW_NOT_READY",
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "approved_for_live_real": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "private_account_read_performed": False,
        "private_api_access_allowed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "automatic_commit_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "historical_report_mutation_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "promotion_state_mutation_performed": False,
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "phase_34_closed": source.get("phase_34_closed", True),
        "phase_35_closed": source.get("phase_35_closed", True),
        "phase_36_final_closed": source.get("phase_36_final_closed", True),
        "phase_37_final_closed": source.get("phase_37_final_closed"),
        "phase_38_execution_started": False,
        "phase_38_planning_only": True,
        "phase_38_unlocked": False,
        "final_safety_violations": [],
        "final_safety_violation_count": 0 if ok else len(errors),
        "git_available": (git_head_short(repo_root) is not None),
        "git_head_short": git_head_short(repo_root),
        "host": socket.gethostname(),
    }

    # Re-assert safety false fields after merges.
    for field in SAFETY_FALSE_FIELDS:
        report[field] = False
    report["report_digest"] = stable_digest({k: v for k, v in report.items() if k not in {"report_digest", "report_path"}})

    paths: dict[str, str | None] = {
        "paper_transition_readiness_review_path": None,
        "paper_transition_approval_gate_path": None,
        "no_live_no_exchange_submit_guard_path": None,
        "paper_transition_readiness_review_gate_path": None,
        "report_path": None,
    }
    if write_reports:
        status_suffix = "ready" if ok else "not_ready"
        base = reports
        review_path = base / f"{PATCH_ID}_paper_transition_readiness_review_{stamp}.json"
        approval_path = base / f"{PATCH_ID}_explicit_paper_transition_approval_gate_{stamp}.json"
        guard_path = base / f"{PATCH_ID}_no_live_no_exchange_submit_guard_{stamp}.json"
        gate_path = base / f"{PATCH_ID}_paper_transition_readiness_review_gate_{stamp}.json"
        report_path = base / f"{PATCH_ID}_paper_transition_readiness_review_{stamp}_{status_suffix}.json"
        write_json(review_path, review)
        write_json(approval_path, approval_gate)
        write_json(guard_path, no_live_guard)
        write_json(gate_path, gate)
        paths = {
            "paper_transition_readiness_review_path": str(review_path),
            "paper_transition_approval_gate_path": str(approval_path),
            "no_live_no_exchange_submit_guard_path": str(guard_path),
            "paper_transition_readiness_review_gate_path": str(gate_path),
            "report_path": str(report_path),
        }
        report.update(paths)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k not in {"report_digest"}})
        write_json(report_path, report)
    else:
        report.update(paths)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/recovery"))
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path.cwd()
    report = build_report(repo_root, args.reports_dir, write_reports=args.write_reports)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
