from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradebot.archive_execution_preflight import build_archive_execution_preflight_report, summarize_report


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_33g_accepts_full_33f_nested_run_report(tmp_path: Path) -> None:
    (tmp_path / "tools" / "_patch_backup_4B436633F_H1_20260702T000000Z").mkdir(parents=True)
    (tmp_path / "tools" / "_patch_backup_4B436633F_H1_20260702T000000Z" / "sample.txt").write_text("x", encoding="utf-8")
    _write(
        tmp_path / "reports" / "recovery" / "4B436633F_evidence_retention_archive_policy_20260702T000000Z_ready.json",
        {
            "patch_id": "4B436633F",
            "patch_version": "4B.4.3.6.6.33F",
            "status": "READY",
            "decision": "EVIDENCE_RETENTION_ARCHIVE_POLICY_READY_NON_DESTRUCTIVE_PLAN_COMPLETE",
            "source_33e": {"complete": True},
            "retention_rules_complete": True,
            "report_retention": {"complete": True},
            "backup_payload_archive_manifest": {"complete": True},
            "non_destructive_cleanup_plan": {"complete": True, "destructive_cleanup_performed": False},
            "evidence_aging_ledger": {"complete": True},
            "safety_snapshot": {
                "destructive_cleanup_performed": False,
                "exchange_submit_performed": False,
                "trading_action_performed": False,
                "training_performed": False,
                "reload_performed": False,
                "runtime_overlay_activated": False,
            },
        },
    )
    report = build_archive_execution_preflight_report(tmp_path)
    summary = summarize_report(report)
    assert summary["source_33f_complete"] is True
    assert summary["status"] == "READY"
    assert summary["decision"] == "ARCHIVE_EXECUTION_PREFLIGHT_READY_DRY_RUN_VALIDATED"
    assert summary["archive_execution_allowed"] is False
    assert summary["archive_move_performed"] is False
    assert summary["file_delete_performed"] is False


def test_33g_still_blocks_destructive_33f_report(tmp_path: Path) -> None:
    _write(
        tmp_path / "reports" / "recovery" / "4B436633F_evidence_retention_archive_policy_20260702T000001Z_ready.json",
        {
            "status": "READY",
            "decision": "EVIDENCE_RETENTION_ARCHIVE_POLICY_READY_NON_DESTRUCTIVE_PLAN_COMPLETE",
            "source_33e_complete": True,
            "retention_rules_complete": True,
            "report_retention_complete": True,
            "backup_payload_archive_manifest_complete": True,
            "non_destructive_cleanup_plan_complete": True,
            "evidence_aging_ledger_complete": True,
            "destructive_cleanup_performed": True,
        },
    )
    report = build_archive_execution_preflight_report(tmp_path)
    assert report.source_33f_complete is False
    assert report.status == "NOT_READY"


def test_missing_operator_approval_is_dry_run_only_not_execution_permission(tmp_path: Path) -> None:
    _write(
        tmp_path / "reports" / "recovery" / "4B436633F_evidence_retention_archive_policy_20260702T000002Z_ready.json",
        {
            "status": "READY",
            "decision": "EVIDENCE_RETENTION_ARCHIVE_POLICY_READY_NON_DESTRUCTIVE_PLAN_COMPLETE",
            "source_33e_complete": True,
            "retention_rules_complete": True,
            "report_retention_complete": True,
            "backup_payload_archive_manifest_complete": True,
            "non_destructive_cleanup_plan_complete": True,
            "evidence_aging_ledger_complete": True,
            "destructive_cleanup_performed": False,
        },
    )
    report = build_archive_execution_preflight_report(tmp_path)
    assert report.operator_approved_archive_plan_validator.operator_approval_present is False
    assert report.operator_approved_archive_plan_validator.operator_approval_status == "APPROVAL_NOT_PRESENT_DRY_RUN_ONLY"
    assert report.archive_execution_allowed is False
    assert report.status == "READY"
