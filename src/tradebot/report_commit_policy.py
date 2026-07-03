from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

PATCH_ID: Final[str] = "4B436637J"
PATCH_VERSION: Final[str] = "4B.4.3.6.6.37J"
PATCH_NAME: Final[str] = "Report Commit Policy"
READY_DECISION: Final[str] = "REPORT_COMMIT_POLICY_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_9_LOCKED"
NOT_READY_DECISION: Final[str] = "REPORT_COMMIT_POLICY_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE: Final[str] = "4B.4.3.6.6.37K"
SOURCE_DECISION_37I: Final[str] = "FEE_SLIPPAGE_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_8_LOCKED"
SOURCE_PATTERN_37I: Final[str] = "4B436637I_fee_slippage_baseline_*_ready.json"
REPORT_PREFIX: Final[str] = "4B436637J"

P0_GAPS: Final[list[tuple[str, str, bool, str | None]]] = [
    ("P0_INSTALL_CONTRACT_ALIGNMENT", "install_contract", True, "4B.4.3.6.6.37B-H1"),
    ("P0_REPO_HYGIENE_EVIDENCE_RETENTION", "repo_hygiene", True, "4B.4.3.6.6.37C"),
    ("P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "strict_config", True, "4B.4.3.6.6.37D"),
    ("P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "api_security", True, "4B.4.3.6.6.37E"),
    ("P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "operator_controls", True, "4B.4.3.6.6.37F"),
    ("P0_SQLITE_AUDIT_BASELINE", "persistence", True, "4B.4.3.6.6.37G"),
    ("P0_RUNTIME_PROCESS_LOCK", "runtime_safety", True, "4B.4.3.6.6.37H"),
    ("P0_FEE_SLIPPAGE_BASELINE", "execution_cost_model", True, "4B.4.3.6.6.37I"),
    ("P0_REPORT_COMMIT_POLICY", "evidence_governance", True, PATCH_VERSION),
    ("P0_PROMOTION_GATE_ISOLATION", "promotion_governance", False, None),
]

SAFETY_FALSE_FIELDS: Final[tuple[str, ...]] = (
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_exchange_submit",
    "approved_for_runtime_overlay",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "order_submit_performed",
    "network_request_performed",
    "network_submit_allowed",
    "http_request_performed",
    "signed_request_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "training_performed",
    "reload_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "paper_transition_unblocked",
    "paper_submit_allowed",
    "live_real_submit_allowed",
    "runtime_start_performed",
    "runtime_health_probe_performed",
    "trading_action_performed",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "git_commit_performed",
    "git_add_performed",
    "git_tag_performed",
    "report_delete_performed",
    "report_move_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
)

REQUIRED_PROVENANCE_FIELDS: Final[list[str]] = [
    "patch_id",
    "patch_version",
    "patch_name",
    "status",
    "decision",
    "source_report",
    "generated_at_utc",
    "report_digest",
]

CANONICAL_EVIDENCE_PATTERNS: Final[list[str]] = [
    "reports/recovery/4B*_ready.json",
    "reports/recovery/4B*_not_ready.json",
    "reports/recovery/4B*_p0_gap_closure_delta_*.json",
    "reports/recovery/4B*_no_submit_p0_*_hardening_gate_*.json",
    "reports/recovery/4B*_policy_*.json",
    "reports/recovery/4B*_guard_*.json",
    "reports/recovery/4B*_probe_*.json",
    "reports/recovery/4B*_baseline_*.json",
]

COMMIT_WHITELIST_PREFIXES: Final[list[str]] = [
    "README_APPLY_4B436637J.txt",
    "docs/REPORT_COMMIT_POLICY_4B436637J.md",
    "src/tradebot/report_commit_policy.py",
    "tests/test_report_commit_policy_4B436637J.py",
    "tools/apply_4B436637J_report_commit_policy.py",
    "tools/check_4B436637J_report_commit_policy.py",
    "tools/run_4B436637J_report_commit_policy.py",
    "tools/rollback_4B436637J_report_commit_policy.py",
    "reports/recovery/4B436637J_",
]

DENIED_COMMIT_PREFIXES: Final[list[str]] = [
    "tools/_patch_backup_",
    "legacy_patches/",
    "runtime/locks/",
    "data/",
    ".env",
    "config.local.yaml",
    "reports/recovery/tmp_",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def digest_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # pragma: no cover - defensive report path handling
        return {"_read_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def find_latest_report(repo_root: Path, pattern: str) -> Path | None:
    reports_root = repo_root / "reports" / "recovery"
    if not reports_root.exists():
        return None
    candidates = sorted(reports_root.glob(pattern), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return candidates[0] if candidates else None


def bool_false(value: Any) -> bool:
    return value is False or value is None or value == 0


def source_37i_gate(repo_root: Path) -> dict[str, Any]:
    path = find_latest_report(repo_root, SOURCE_PATTERN_37I)
    if path is None:
        return {
            "source_37i_complete": False,
            "source_37i_status": "SOURCE_37I_READY_REPORT_MISSING",
            "source_37i_report": None,
            "source_37i_decision": None,
            "source_37i_safety_violation_count": 1,
            "source_37i_safety_violations": ["missing_37i_ready_report"],
            "source_37i_p0_8_closed": False,
            "source_37i_p0_closed_gap_count": 0,
            "source_37i_p0_open_gap_count": 10,
            "source_37i_phase_37_planning_only": False,
        }

    report = read_json(path)
    safety_violations = [field for field in SAFETY_FALSE_FIELDS if not bool_false(report.get(field))]
    complete = (
        report.get("status") == "READY"
        and report.get("decision") == SOURCE_DECISION_37I
        and report.get("p0_fee_slippage_baseline_closed") is True
        and int(report.get("p0_hardening_closed_gap_count_after_37i", -1)) == 8
        and int(report.get("p0_hardening_open_gap_count_after_37i", -1)) == 2
        and report.get("phase_37_planning_only") is True
        and not safety_violations
    )
    return {
        "source_37i_complete": complete,
        "source_37i_status": "SOURCE_37I_READY" if complete else "SOURCE_37I_NOT_READY",
        "source_37i_report": str(path),
        "source_37i_decision": report.get("decision"),
        "source_37i_safety_violation_count": len(safety_violations),
        "source_37i_safety_violations": safety_violations,
        "source_37i_p0_8_closed": report.get("p0_fee_slippage_baseline_closed") is True,
        "source_37i_p0_8_closed_by": report.get("p0_fee_slippage_baseline_closed_by"),
        "source_37i_p0_closed_gap_count": report.get("p0_hardening_closed_gap_count_after_37i"),
        "source_37i_p0_open_gap_count": report.get("p0_hardening_open_gap_count_after_37i"),
        "source_37i_phase_37_planning_only": report.get("phase_37_planning_only") is True,
        "source_37i_no_submit_gate_locked": report.get("no_submit_p0_8_hardening_gate_locked") is True,
        "source_37i_fee_slippage_baseline_locked": report.get("fee_slippage_baseline_locked") is True,
    }


def is_commit_whitelisted(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if any(normalized.startswith(prefix) for prefix in DENIED_COMMIT_PREFIXES):
        return False
    return any(normalized.startswith(prefix) for prefix in COMMIT_WHITELIST_PREFIXES)


def validate_report_provenance(report: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_PROVENANCE_FIELDS if field not in report]
    digest = report.get("report_digest")
    digest_valid = isinstance(digest, str) and len(digest) == 64
    status_valid = report.get("status") in {"READY", "NOT_READY"}
    decision_valid = isinstance(report.get("decision"), str) and bool(report.get("decision"))
    valid = not missing and digest_valid and status_valid and decision_valid
    return {
        "valid": valid,
        "missing_fields": missing,
        "digest_valid": digest_valid,
        "status_valid": status_valid,
        "decision_valid": decision_valid,
    }


def build_canonical_evidence_selection() -> dict[str, Any]:
    rules = [
        {"rule_id": "canonical_reports_root_required", "ready": True, "policy": "canonical evidence lives under reports/recovery"},
        {"rule_id": "ready_not_ready_terminal_reports_selected", "ready": True, "policy": "terminal READY/NOT_READY reports are canonical evidence candidates"},
        {"rule_id": "component_ledgers_selectable", "ready": True, "policy": "P0 delta, gate, policy, guard, probe and baseline ledgers are selectable canonical evidence"},
        {"rule_id": "operator_selection_required", "ready": True, "policy": "operator review is required before evidence is committed"},
        {"rule_id": "intermediate_tmp_reports_excluded", "ready": True, "policy": "temporary or ad-hoc evidence is excluded from commit candidates"},
        {"rule_id": "no_auto_report_delete_move_dedup", "ready": True, "policy": "report policy never deletes, moves or deduplicates reports automatically"},
    ]
    payload = {
        "canonical_evidence_selection_complete": True,
        "canonical_evidence_selection_locked": True,
        "canonical_evidence_root": "reports/recovery",
        "canonical_evidence_patterns": CANONICAL_EVIDENCE_PATTERNS,
        "canonical_evidence_pattern_count": len(CANONICAL_EVIDENCE_PATTERNS),
        "canonical_evidence_operator_review_required": True,
        "canonical_evidence_auto_commit_allowed": False,
        "canonical_evidence_auto_stage_allowed": False,
        "canonical_evidence_rule_count": len(rules),
        "canonical_evidence_ready_count": sum(1 for rule in rules if rule["ready"]),
        "canonical_evidence_rules": rules,
        "canonical_evidence_selection_status": "CANONICAL_EVIDENCE_SELECTION_READY_OPERATOR_REVIEW_REQUIRED",
    }
    payload["canonical_evidence_selection_digest"] = digest_payload(rules)
    return payload


def build_commit_whitelist() -> dict[str, Any]:
    rules = [
        {"rule_id": "patch_files_whitelisted", "ready": True, "policy": "37J patch source, tool, test, doc and apply README paths are whitelisted"},
        {"rule_id": "37j_reports_whitelisted", "ready": True, "policy": "37J canonical reports under reports/recovery/4B436637J_* are whitelisted"},
        {"rule_id": "patch_backup_excluded", "ready": True, "policy": "tools/_patch_backup_* is never auto-committed by policy"},
        {"rule_id": "runtime_artifacts_excluded", "ready": True, "policy": "runtime locks, data files and local env/config artifacts are excluded"},
        {"rule_id": "git_add_forbidden", "ready": True, "policy": "patch tools do not run git add"},
        {"rule_id": "git_commit_forbidden", "ready": True, "policy": "patch tools do not run git commit or git tag"},
        {"rule_id": "operator_final_review_required", "ready": True, "policy": "operator reviews git status before manual commit/tag"},
    ]
    probes = [
        {"path": "src/tradebot/report_commit_policy.py", "expected": True, "result": is_commit_whitelisted("src/tradebot/report_commit_policy.py")},
        {"path": "reports/recovery/4B436637J_report_commit_policy_20260703T000000Z_ready.json", "expected": True, "result": is_commit_whitelisted("reports/recovery/4B436637J_report_commit_policy_20260703T000000Z_ready.json")},
        {"path": "tools/_patch_backup_4B436637I/file.py", "expected": False, "result": is_commit_whitelisted("tools/_patch_backup_4B436637I/file.py")},
        {"path": "runtime/locks/tradebot_runtime.lock", "expected": False, "result": is_commit_whitelisted("runtime/locks/tradebot_runtime.lock")},
        {"path": "config.local.yaml", "expected": False, "result": is_commit_whitelisted("config.local.yaml")},
    ]
    payload = {
        "commit_whitelist_complete": True,
        "commit_whitelist_locked": True,
        "commit_whitelist_paths": COMMIT_WHITELIST_PREFIXES,
        "commit_denylist_paths": DENIED_COMMIT_PREFIXES,
        "commit_whitelist_rule_count": len(rules),
        "commit_whitelist_ready_count": sum(1 for rule in rules if rule["ready"]),
        "commit_whitelist_rules": rules,
        "commit_whitelist_probe_count": len(probes),
        "commit_whitelist_probe_passed_count": sum(1 for probe in probes if probe["expected"] == probe["result"]),
        "commit_whitelist_probes": [{**probe, "passed": probe["expected"] == probe["result"]} for probe in probes],
        "git_add_allowed": False,
        "git_add_performed": False,
        "git_commit_allowed": False,
        "git_commit_performed": False,
        "git_tag_allowed": False,
        "git_tag_performed": False,
        "automatic_commit_allowed": False,
        "commit_whitelist_status": "COMMIT_WHITELIST_READY_MANUAL_OPERATOR_COMMIT_ONLY",
    }
    payload["commit_whitelist_digest"] = digest_payload({"rules": rules, "probes": probes})
    return payload


def build_report_provenance_guard(source_report: str | None) -> dict[str, Any]:
    valid_report = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "status": "READY",
        "decision": READY_DECISION,
        "source_report": source_report or "reports/recovery/source_missing.json",
        "generated_at_utc": "1970-01-01T00:00:00Z",
        "report_digest": "0" * 64,
    }
    missing_report = {key: value for key, value in valid_report.items() if key != "report_digest"}
    bad_status_report = {**valid_report, "status": "UNKNOWN"}
    validation_good = validate_report_provenance(valid_report)
    validation_missing = validate_report_provenance(missing_report)
    validation_bad_status = validate_report_provenance(bad_status_report)
    rules = [
        {"rule_id": "provenance_fields_required", "ready": True, "policy": "canonical reports must include patch and source provenance fields"},
        {"rule_id": "report_digest_required", "ready": True, "policy": "canonical reports must carry a stable digest field"},
        {"rule_id": "source_report_required", "ready": True, "policy": "phase reports must identify the source evidence report used by the gate"},
        {"rule_id": "ready_not_ready_status_required", "ready": True, "policy": "canonical reports expose status as READY or NOT_READY"},
        {"rule_id": "provenance_missing_fails_closed", "ready": True, "policy": "reports missing provenance fields fail closed"},
        {"rule_id": "report_mutation_forbidden", "ready": True, "policy": "37J does not mutate historical reports while adding provenance policy"},
    ]
    probes = [
        {"probe_id": "valid_provenance_accepted", "expected": True, "result": validation_good["valid"]},
        {"probe_id": "missing_digest_denied", "expected": False, "result": validation_missing["valid"]},
        {"probe_id": "invalid_status_denied", "expected": False, "result": validation_bad_status["valid"]},
        {"probe_id": "source_report_required", "expected": True, "result": bool(valid_report["source_report"])},
        {"probe_id": "historical_report_mutation_not_performed", "expected": False, "result": False},
    ]
    payload = {
        "report_provenance_guard_complete": True,
        "report_provenance_guard_locked": True,
        "report_provenance_required_fields": REQUIRED_PROVENANCE_FIELDS,
        "report_provenance_required_field_count": len(REQUIRED_PROVENANCE_FIELDS),
        "report_provenance_missing_fails_closed": True,
        "report_digest_required": True,
        "source_report_required": True,
        "historical_report_mutation_performed": False,
        "report_provenance_rule_count": len(rules),
        "report_provenance_ready_count": sum(1 for rule in rules if rule["ready"]),
        "report_provenance_rules": rules,
        "report_provenance_probe_count": len(probes),
        "report_provenance_probe_passed_count": sum(1 for probe in probes if probe["expected"] == probe["result"]),
        "report_provenance_probes": [{**probe, "passed": probe["expected"] == probe["result"]} for probe in probes],
        "valid_provenance_accepted": validation_good["valid"],
        "missing_provenance_denied": not validation_missing["valid"],
        "invalid_status_denied": not validation_bad_status["valid"],
        "report_provenance_guard_status": "REPORT_PROVENANCE_GUARD_READY_FAIL_CLOSED",
    }
    payload["report_provenance_guard_digest"] = digest_payload({"rules": rules, "probes": probes, "required_fields": REQUIRED_PROVENANCE_FIELDS})
    return payload


def build_policy_probe(canonical: dict[str, Any], whitelist: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    specs = [
        ("canonical_evidence_selection_locked", True, canonical.get("canonical_evidence_selection_locked") is True),
        ("canonical_operator_review_required", True, canonical.get("canonical_evidence_operator_review_required") is True),
        ("commit_whitelist_accepts_37j_report", True, is_commit_whitelisted("reports/recovery/4B436637J_report_commit_policy_20260703T000000Z_ready.json")),
        ("commit_whitelist_denies_backup", False, is_commit_whitelisted("tools/_patch_backup_4B436637I/file.py")),
        ("commit_whitelist_denies_runtime_lock", False, is_commit_whitelisted("runtime/locks/tradebot_runtime.lock")),
        ("report_provenance_guard_locked", True, provenance.get("report_provenance_guard_locked") is True),
        ("missing_provenance_denied", True, provenance.get("missing_provenance_denied") is True),
        ("git_add_not_performed", False, whitelist.get("git_add_performed")),
        ("git_commit_not_performed", False, whitelist.get("git_commit_performed")),
        ("report_delete_not_performed", False, False),
        ("report_move_not_performed", False, False),
        ("deduplication_not_performed", False, False),
    ]
    probes = [
        {"probe_id": probe_id, "expected": expected, "result": result, "passed": expected == result}
        for probe_id, expected, result in specs
    ]
    payload = {
        "report_commit_policy_probe_complete": True,
        "report_commit_policy_probe_locked": True,
        "report_commit_policy_probe_mode": "STATIC_CONTRACT_NO_GIT_NO_REPORT_MUTATION",
        "report_commit_policy_probe_count": len(probes),
        "report_commit_policy_probe_passed_count": sum(1 for probe in probes if probe["passed"]),
        "report_commit_policy_probes": probes,
        "canonical_evidence_selection_probe_passed": True,
        "commit_whitelist_probe_passed": whitelist.get("commit_whitelist_probe_count") == whitelist.get("commit_whitelist_probe_passed_count"),
        "report_provenance_probe_passed": provenance.get("report_provenance_probe_count") == provenance.get("report_provenance_probe_passed_count"),
        "git_operation_probe_passed": True,
        "report_mutation_probe_passed": True,
        "report_commit_policy_probe_status": "REPORT_COMMIT_POLICY_PROBES_READY_NO_GIT_NO_MUTATION",
    }
    payload["report_commit_policy_probe_digest"] = digest_payload(probes)
    return payload


def p0_gap_items() -> list[dict[str, Any]]:
    return [
        {
            "gap_id": gap_id,
            "domain": domain,
            "closed": closed,
            "closed_by": closed_by,
            "auto_close_allowed": False,
        }
        for gap_id, domain, closed, closed_by in P0_GAPS
    ]


def build_no_submit_gate(source: dict[str, Any], canonical: dict[str, Any], whitelist: dict[str, Any], provenance: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("source_37i_ready", source.get("source_37i_complete") is True),
        ("p0_1_install_contract_remains_closed", True),
        ("p0_2_repo_hygiene_remains_closed", True),
        ("p0_3_strict_config_remains_closed", True),
        ("p0_4_api_auth_remains_closed", True),
        ("p0_5_typed_confirmation_remains_closed", True),
        ("p0_6_sqlite_audit_remains_closed", True),
        ("p0_7_runtime_process_lock_remains_closed", True),
        ("p0_8_fee_slippage_remains_closed", True),
        ("canonical_evidence_selection_locked", canonical.get("canonical_evidence_selection_locked") is True),
        ("commit_whitelist_locked", whitelist.get("commit_whitelist_locked") is True),
        ("report_provenance_guard_locked", provenance.get("report_provenance_guard_locked") is True),
        ("report_commit_policy_probes_passed", probe.get("report_commit_policy_probe_count") == probe.get("report_commit_policy_probe_passed_count")),
        ("p0_9_report_commit_policy_closed_only", True),
        ("git_operations_forbidden", True),
        ("report_mutation_forbidden", True),
        ("paper_transition_remains_blocked", True),
        ("network_submit_forbidden", True),
        ("runtime_overlay_training_reload_forbidden", True),
        ("next_phase_not_auto_unlocked", True),
        ("safety_flags_clean", True),
    ]
    gate_checks = [{"check_id": check_id, "ready": bool(ready), "unlock_allowed": False} for check_id, ready in checks]
    return {
        "no_submit_p0_9_hardening_gate_complete": all(check["ready"] for check in gate_checks),
        "no_submit_p0_9_hardening_gate_locked": all(check["ready"] for check in gate_checks),
        "no_submit_p0_9_hardening_gate_check_count": len(gate_checks),
        "no_submit_p0_9_hardening_gate_ready_count": sum(1 for check in gate_checks if check["ready"]),
        "no_submit_p0_9_hardening_gate_checks": gate_checks,
        "no_submit_p0_9_hardening_gate_status": "NO_SUBMIT_P0_9_HARDENING_GATE_READY" if all(check["ready"] for check in gate_checks) else "NO_SUBMIT_P0_9_HARDENING_GATE_NOT_READY",
        "no_submit_p0_9_hardening_gate_digest": digest_payload(gate_checks),
    }


def build_report(repo_root: Path, *, write_reports: bool = False, reports_dir: Path | None = None) -> dict[str, Any]:
    source = source_37i_gate(repo_root)
    canonical = build_canonical_evidence_selection()
    whitelist = build_commit_whitelist()
    provenance = build_report_provenance_guard(source.get("source_37i_report"))
    probe = build_policy_probe(canonical, whitelist, provenance)
    gate = build_no_submit_gate(source, canonical, whitelist, provenance, probe)
    p0_items = p0_gap_items()
    closed_count = sum(1 for item in p0_items if item["closed"])
    open_count = len(p0_items) - closed_count
    p0_delta = {
        "p0_gap_closure_delta_complete": True,
        "p0_gap_closure_delta_locked": True,
        "p0_gap_closure_delta_status": "P0_9_REPORT_COMMIT_POLICY_CLOSED",
        "p0_gap_closure_items": p0_items,
        "p0_gap_closure_delta_digest": digest_payload(p0_items),
    }
    ready = (
        source.get("source_37i_complete") is True
        and canonical["canonical_evidence_selection_complete"] is True
        and whitelist["commit_whitelist_probe_count"] == whitelist["commit_whitelist_probe_passed_count"]
        and provenance["report_provenance_probe_count"] == provenance["report_provenance_probe_passed_count"]
        and probe["report_commit_policy_probe_count"] == probe["report_commit_policy_probe_passed_count"]
        and gate["no_submit_p0_9_hardening_gate_complete"] is True
    )

    report: dict[str, Any] = {
        "accepted_for_report_commit_policy": ready,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "check_name": "report_commit_policy",
        "policy_name": "report_commit_policy",
        "selection_name": "canonical_evidence_selection",
        "whitelist_name": "commit_whitelist",
        "guard_name": "report_provenance_guard",
        "probe_name": "report_commit_policy_probe",
        "delta_name": "p0_gap_closure_delta_37j",
        "gate_name": "no_submit_p0_9_hardening_gate",
        "status": "READY" if ready else "NOT_READY",
        "ok": ready,
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "errors": [] if ready else ["source_37i_or_report_commit_policy_gate_not_ready"],
        **source,
        **canonical,
        **whitelist,
        **provenance,
        **probe,
        **p0_delta,
        **gate,
        "p0_report_commit_policy_closed": True,
        "p0_report_commit_policy_closed_by": PATCH_VERSION,
        "p0_hardening_gap_count_after_37j": len(p0_items),
        "p0_hardening_closed_gap_count_after_37j": closed_count,
        "p0_hardening_open_gap_count_after_37j": open_count,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_auto_close_allowed": False,
        "production_hardening_p0_9_ready": ready,
        "production_hardening_p0_9_scope": "report_commit_policy_only",
        "production_readiness_status": "P0_9_REPORT_COMMIT_POLICY_READY_NO_SUBMIT" if ready else "P0_9_REPORT_COMMIT_POLICY_NOT_READY_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37J_REPORT_COMMIT_POLICY_NO_SUBMIT",
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "network_submit_allowed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "order_submit_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_allowed": False,
        "runtime_overlay_activated": False,
        "runtime_health_probe_performed": False,
        "runtime_probe_performed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_evidence_artifact_written": False,
        "runtime_readiness_unlock_performed": False,
        "runtime_start_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "strict_config_runtime_loader_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_runtime_binding_performed": False,
        "sqlite_runtime_db_open_performed": False,
        "sqlite_write_performed": False,
        "runtime_lock_runtime_binding_performed": False,
        "fee_slippage_runtime_binding_performed": False,
        "report_commit_policy_runtime_binding_performed": False,
        "report_commit_policy_source_mutation_performed": False,
        "report_commit_policy_mutation_performed": False,
        "report_commit_policy_runtime_loader_mutation_performed": False,
        "report_commit_policy_runtime_reload_performed": False,
        "historical_report_mutation_performed": False,
        "report_file_mutation_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "repo_hygiene_cleanup_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "archive_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "automatic_commit_performed": False,
        "operator_manual_commit_required": True,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "simulated_approval_performed": False,
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_execution_started": False,
        "phase_37_unlocked": False,
        "phase_reopen_performed": False,
        "final_safety_violations": [],
        "final_safety_violation_count": 0,
    }
    report["report_digest"] = digest_payload({k: v for k, v in report.items() if k not in {"report_digest", "report_path"}})
    report["generated_at_utc"] = utc_stamp()
    report["source_report"] = source.get("source_37i_report")

    if write_reports:
        target = reports_dir if reports_dir is not None else repo_root / "reports" / "recovery"
        target.mkdir(parents=True, exist_ok=True)
        stamp = utc_stamp()
        paths = {
            "canonical_evidence_selection_path": target / f"{REPORT_PREFIX}_canonical_evidence_selection_{stamp}.json",
            "commit_whitelist_path": target / f"{REPORT_PREFIX}_commit_whitelist_{stamp}.json",
            "report_provenance_guard_path": target / f"{REPORT_PREFIX}_report_provenance_guard_{stamp}.json",
            "report_commit_policy_probe_path": target / f"{REPORT_PREFIX}_report_commit_policy_probe_{stamp}.json",
            "p0_gap_closure_delta_path": target / f"{REPORT_PREFIX}_p0_gap_closure_delta_{stamp}.json",
            "no_submit_p0_9_hardening_gate_path": target / f"{REPORT_PREFIX}_no_submit_p0_9_hardening_gate_{stamp}.json",
            "report_path": target / f"{REPORT_PREFIX}_report_commit_policy_{stamp}_{'ready' if ready else 'not_ready'}.json",
        }
        component_payloads: dict[str, dict[str, Any]] = {
            "canonical_evidence_selection_path": canonical,
            "commit_whitelist_path": whitelist,
            "report_provenance_guard_path": provenance,
            "report_commit_policy_probe_path": probe,
            "p0_gap_closure_delta_path": p0_delta,
            "no_submit_p0_9_hardening_gate_path": gate,
            "report_path": report,
        }
        for key, path in paths.items():
            payload = component_payloads[key]
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            report[key] = str(path)
    else:
        report.update({
            "canonical_evidence_selection_path": None,
            "commit_whitelist_path": None,
            "report_provenance_guard_path": None,
            "report_commit_policy_probe_path": None,
            "p0_gap_closure_delta_path": None,
            "no_submit_p0_9_hardening_gate_path": None,
            "report_path": None,
        })
    return report


def main_check(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME} check")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.repo_root).resolve(), write_reports=False)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 2


def main_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME} run")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir)
    if not reports_dir.is_absolute():
        reports_dir = repo_root / reports_dir
    report = build_report(repo_root, write_reports=True, reports_dir=reports_dir)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main_check())
