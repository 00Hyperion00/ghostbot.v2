
from __future__ import annotations

import json
from pathlib import Path

from tradebot.archive_execution_approval_ledger import (
    READY_DECISION,
    build_archive_execution_approval_ledger_report,
    summarize_report,
    write_archive_execution_approval_ledger_report,
)


def _write_source_33g(repo: Path) -> Path:
    reports = repo / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "4B436633G_archive_execution_preflight_20260702T000000Z_ready.json"
    payload = {
        "status": "READY",
        "decision": "ARCHIVE_EXECUTION_PREFLIGHT_READY_DRY_RUN_VALIDATED",
        "source_33f_complete": True,
        "archive_execution_preflight_complete": True,
        "dry_run_archive_move_preview_complete": True,
        "dry_run_archive_move_record_count": 2,
        "dry_run_archive_total_file_count": 9,
        "dry_run_archive_total_size_bytes": 12345,
        "manifest_hash_verification_complete": True,
        "manifest_missing_source_count": 0,
        "manifest_sha256": "a" * 64,
        "rollback_plan_complete": True,
        "rollback_record_count": 2,
        "operator_approval_present": False,
        "operator_approval_status": "APPROVAL_NOT_PRESENT_DRY_RUN_ONLY",
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_archive_execution_approval_ledger_ready_without_token(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TRADEBOT_ARCHIVE_APPROVAL_TOKEN", raising=False)
    _write_source_33g(tmp_path)
    report = build_archive_execution_approval_ledger_report(tmp_path)
    summary = summarize_report(report)
    assert report.ok is True
    assert report.decision == READY_DECISION
    assert summary["source_33g_complete"] is True
    assert summary["human_approval_token_status"] == "APPROVAL_TOKEN_NOT_PRESENT_NO_EXECUTION_ONLY"
    assert summary["archive_execution_allowed"] is False
    assert summary["archive_move_performed"] is False
    assert summary["file_delete_performed"] is False


def test_archive_execution_approval_ledger_invalid_token_fails_closed(tmp_path: Path, monkeypatch) -> None:
    _write_source_33g(tmp_path)
    monkeypatch.setenv("TRADEBOT_ARCHIVE_APPROVAL_TOKEN", "bad-token")
    report = build_archive_execution_approval_ledger_report(tmp_path)
    summary = summarize_report(report)
    assert report.ok is False
    assert summary["human_approval_token_status"] == "APPROVAL_TOKEN_INVALID_NO_EXECUTION_ALLOWED"
    assert summary["archive_execution_allowed"] is False
    assert summary["file_delete_performed"] is False


def test_archive_execution_approval_ledger_write_outputs_ledgers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TRADEBOT_ARCHIVE_APPROVAL_TOKEN", raising=False)
    _write_source_33g(tmp_path)
    summary = write_archive_execution_approval_ledger_report(tmp_path, tmp_path / "reports" / "recovery")
    assert summary["ok"] is True
    for key in [
        "report_path",
        "human_approval_token_ledger_path",
        "immutable_plan_digest_ledger_path",
        "final_no_execution_gate_path",
    ]:
        assert Path(summary[key]).exists()
