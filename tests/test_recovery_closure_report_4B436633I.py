from __future__ import annotations

import json
from pathlib import Path

from tradebot.recovery_closure_report import (
    READY_DECISION,
    build_recovery_closure_report,
    build_source_33h_gate,
    summarize_report,
    write_recovery_closure_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_required_files(root: Path) -> None:
    for relative in (
        "src/tradebot/recovery_closure_report.py",
        "tools/check_4B436633I_recovery_closure_report.py",
        "tools/run_4B436633I_recovery_closure_report.py",
        "tests/test_recovery_closure_report_4B436633I.py",
        "docs/RECOVERY_CLOSURE_REPORT_4B436633I.md",
        "README_APPLY_4B436633I.txt",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("placeholder", encoding="utf-8")


def _seed_phase_reports(root: Path) -> None:
    report_dir = root / "reports" / "recovery"
    _write(report_dir / "4B436633A_project_recovery_baseline_20260703T000000Z_not_ready.json", {"status": "NOT_READY"})
    for name, decision in (
        ("4B436633B_canonical_evidence_phase_hygiene_20260703T000001Z_ready.json", "CANONICAL_EVIDENCE_PHASE_HYGIENE_READY_NO_TRADING_ACTIONS"),
        ("4B436633C_phase_chain_validator_20260703T000002Z_ready.json", "PHASE_CHAIN_VALIDATOR_READY_SUBMIT_CAPABILITY_BLOCKED"),
        ("4B436633D_runtime_safety_lockdown_20260703T000003Z_ready.json", "RUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED"),
        ("4B436633D_H1_destructive_endpoint_guard_hotfix_20260703T000004Z_ready.json", "DESTRUCTIVE_ENDPOINT_GUARD_COVERAGE_HOTFIX_READY"),
        ("4B436633E_status_conflict_resolver_20260703T000005Z_ready.json", "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE"),
        ("4B436633E_H1_source_33d_gate_hotfix_20260703T000006Z_ready.json", "SOURCE_33D_COMPLETION_GATE_HOTFIX_READY"),
        ("4B436633F_evidence_retention_archive_policy_20260703T000007Z_ready.json", "EVIDENCE_RETENTION_ARCHIVE_POLICY_READY_NON_DESTRUCTIVE_PLAN_COMPLETE"),
        ("4B436633F_H1_source_33e_gate_hotfix_20260703T000008Z_ready.json", "SOURCE_33E_COMPLETION_GATE_HOTFIX_READY"),
        ("4B436633G_archive_execution_preflight_20260703T000009Z_ready.json", "ARCHIVE_EXECUTION_PREFLIGHT_READY_DRY_RUN_VALIDATED"),
        ("4B436633G_H1_source_33f_gate_hotfix_20260703T000010Z_ready.json", "SOURCE_33F_COMPLETION_GATE_HOTFIX_READY"),
        ("4B436633H_H1_source_33g_gate_hotfix_20260703T000011Z_ready.json", "SOURCE_33G_COMPLETION_GATE_HOTFIX_READY"),
    ):
        _write(report_dir / name, {"status": "READY", "decision": decision, "ok": True})
    _write(
        report_dir / "4B436633H_archive_execution_approval_ledger_20260703T000012Z_ready.json",
        {
            "status": "READY",
            "decision": "ARCHIVE_EXECUTION_APPROVAL_LEDGER_READY_FINAL_NO_EXECUTION_GATE_LOCKED",
            "ok": True,
            "source_33g_complete": True,
            "final_no_execution_gate_complete": True,
            "human_approval_token_ledger_complete": True,
            "human_approval_token_present": False,
            "human_approval_token_status": "APPROVAL_TOKEN_NOT_PRESENT_NO_EXECUTION_ONLY",
            "manifest_sha256": "0" * 64,
            "immutable_plan_digest": "1" * 64,
            "immutable_plan_digest_complete": True,
            "archive_execution_allowed": False,
            "archive_move_performed": False,
            "file_delete_performed": False,
            "destructive_cleanup_performed": False,
            "exchange_submit_performed": False,
            "trading_action_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "runtime_overlay_activated": False,
        },
    )


def test_recovery_closure_ready_without_git_repo(tmp_path: Path) -> None:
    _seed_required_files(tmp_path)
    _seed_phase_reports(tmp_path)
    report = build_recovery_closure_report(tmp_path)
    summary = summarize_report(report)
    assert report.ok is True
    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert summary["source_33h_complete"] is True
    assert summary["accepted_for_closure"] is True
    assert summary["next_phase_unlock_allowed"] is False
    assert summary["archive_execution_allowed"] is False
    assert summary["exchange_submit_performed"] is False


def test_recovery_closure_not_ready_when_33h_missing(tmp_path: Path) -> None:
    _seed_required_files(tmp_path)
    report = build_recovery_closure_report(tmp_path)
    assert report.ok is False
    assert report.status == "NOT_READY"
    assert build_source_33h_gate(tmp_path).complete is False


def test_write_recovery_closure_artifacts(tmp_path: Path) -> None:
    _seed_required_files(tmp_path)
    _seed_phase_reports(tmp_path)
    report, artifacts = write_recovery_closure_report(tmp_path, tmp_path / "reports" / "recovery")
    assert report.ok is True
    assert artifacts.report_path.exists()
    assert artifacts.acceptance_matrix_path.exists()
    assert artifacts.git_tag_audit_path.exists()
    assert artifacts.next_phase_unlock_plan_path.exists()
