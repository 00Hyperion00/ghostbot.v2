from __future__ import annotations

import json
from pathlib import Path

from tradebot.archive_execution_preflight import (
    READY_DECISION,
    build_archive_execution_preflight_report,
    summarize_report,
    write_archive_execution_preflight_report,
)


def _write_33f_ready(repo: Path) -> None:
    reports = repo / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "patch_id": "4B436633F",
        "patch_version": "4B.4.3.6.6.33F",
        "status": "READY",
        "decision": "EVIDENCE_RETENTION_ARCHIVE_POLICY_READY_NON_DESTRUCTIVE_PLAN_COMPLETE",
        "source_33e_complete": True,
        "retention_rules_complete": True,
        "report_retention_complete": True,
        "backup_payload_archive_manifest_complete": True,
        "non_destructive_cleanup_plan_complete": True,
        "evidence_aging_ledger_complete": True,
        "destructive_cleanup_performed": False,
    }
    (reports / "4B436633F_evidence_retention_archive_policy_20260702T000000Z_ready.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_candidates(repo: Path) -> None:
    backup = repo / "tools" / "_patch_backup_4B436633F_H1_20260702T000000Z"
    payload = repo / "tools" / "_patch_payload_4B436633F"
    backup.mkdir(parents=True, exist_ok=True)
    payload.mkdir(parents=True, exist_ok=True)
    (backup / "sample.txt").write_text("backup", encoding="utf-8")
    (payload / "payload.txt").write_text("payload", encoding="utf-8")


def test_archive_execution_preflight_ready_without_execution(tmp_path: Path) -> None:
    _write_33f_ready(tmp_path)
    _write_candidates(tmp_path)
    report = build_archive_execution_preflight_report(tmp_path)
    summary = summarize_report(report)
    assert summary["status"] == "READY"
    assert summary["decision"] == READY_DECISION
    assert summary["source_33f_complete"] is True
    assert summary["dry_run_archive_move_preview_complete"] is True
    assert summary["dry_run_archive_move_record_count"] == 2
    assert summary["archive_execution_allowed"] is False
    assert summary["archive_move_performed"] is False
    assert summary["file_delete_performed"] is False
    assert summary["exchange_submit_performed"] is False


def test_archive_execution_preflight_blocks_invalid_non_dry_run_approval(tmp_path: Path) -> None:
    _write_33f_ready(tmp_path)
    approval = tmp_path / "reports" / "recovery" / "4B436633G_operator_archive_plan_approval.json"
    approval.write_text(
        json.dumps({"operator_approved": True, "requested_action": "execute_archive", "dry_run_only": False}),
        encoding="utf-8",
    )
    report = build_archive_execution_preflight_report(tmp_path)
    summary = summarize_report(report)
    assert summary["status"] == "NOT_READY"
    assert summary["operator_approved_archive_plan_validator_complete"] is False
    assert summary["archive_execution_allowed"] is False


def test_archive_execution_preflight_writes_all_ledgers(tmp_path: Path) -> None:
    _write_33f_ready(tmp_path)
    _write_candidates(tmp_path)
    report, paths = write_archive_execution_preflight_report(tmp_path, tmp_path / "reports" / "recovery")
    assert report.ok is True
    assert set(paths) == {
        "report_path",
        "operator_approved_archive_plan_validator_path",
        "dry_run_archive_move_preview_path",
        "manifest_hash_verification_path",
        "rollback_plan_path",
    }
    for path in paths.values():
        assert Path(path).exists()
