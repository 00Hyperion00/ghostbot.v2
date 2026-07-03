from __future__ import annotations

import json
from pathlib import Path

from tradebot.archive_execution_approval_ledger import build_archive_execution_approval_ledger_report, summarize_report


def _write_33g_full_ready(repo: Path) -> None:
    reports = repo / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "patch_id": "4B436633G",
        "patch_version": "4B.4.3.6.6.33G",
        "status": "READY",
        "decision": "ARCHIVE_EXECUTION_PREFLIGHT_READY_DRY_RUN_VALIDATED",
        "ok": True,
        "source_gate": {"complete": True},
        "source_33f_complete": True,
        "archive_execution_preflight_complete": True,
        "dry_run_archive_move_preview": {
            "complete": True,
            "record_count": 39,
            "total_file_count": 243,
            "total_size_bytes": 4114678,
        },
        "manifest_hash_verification": {
            "complete": True,
            "manifest_sha256": "05fa09bcf15b72d5c383fac82caac1ed8b6db7a5eafbed3eba7598aa6bdafe2d",
            "missing_source_count": 0,
        },
        "rollback_plan": {"complete": True, "rollback_record_count": 39},
        "operator_approved_archive_plan_validator": {
            "complete": True,
            "operator_approval_present": False,
            "operator_approval_status": "APPROVAL_NOT_PRESENT_DRY_RUN_ONLY",
        },
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
    (reports / "4B436633G_archive_execution_preflight_20260702T144117Z_ready.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_33h_accepts_nested_33g_full_report_schema(tmp_path: Path) -> None:
    _write_33g_full_ready(tmp_path)
    report = build_archive_execution_approval_ledger_report(tmp_path)
    summary = summarize_report(report)
    assert summary["status"] == "READY"
    assert summary["source_33g_complete"] is True
    assert summary["immutable_plan_digest_complete"] is True
    assert summary["manifest_sha256"] == "05fa09bcf15b72d5c383fac82caac1ed8b6db7a5eafbed3eba7598aa6bdafe2d"
    assert summary["dry_run_archive_move_record_count"] == 39
    assert summary["dry_run_archive_total_file_count"] == 243
    assert summary["rollback_record_count"] == 39
    assert summary["archive_execution_allowed"] is False
    assert summary["file_delete_performed"] is False


def test_33h_remains_fail_closed_when_nested_execution_flag_true(tmp_path: Path) -> None:
    _write_33g_full_ready(tmp_path)
    path = next((tmp_path / "reports" / "recovery").glob("4B436633G_archive_execution_preflight_*_ready.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["archive_move_performed"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = build_archive_execution_approval_ledger_report(tmp_path)
    summary = summarize_report(report)
    assert summary["status"] == "NOT_READY"
    assert summary["source_33g_complete"] is False
    assert summary["final_no_execution_gate_complete"] is False


def test_33h_remains_fail_closed_when_manifest_missing(tmp_path: Path) -> None:
    _write_33g_full_ready(tmp_path)
    path = next((tmp_path / "reports" / "recovery").glob("4B436633G_archive_execution_preflight_*_ready.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["manifest_hash_verification"]["manifest_sha256"] = None
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = build_archive_execution_approval_ledger_report(tmp_path)
    summary = summarize_report(report)
    assert summary["status"] == "NOT_READY"
    assert summary["source_33g_complete"] is False
    assert summary["immutable_plan_digest_complete"] is False
