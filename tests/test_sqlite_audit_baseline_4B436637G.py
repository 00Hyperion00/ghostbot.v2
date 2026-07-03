from __future__ import annotations

import json
from pathlib import Path

from tradebot.sqlite_audit_baseline import (
    PATCH_VERSION,
    READY_DECISION,
    SOURCE_37F_DECISION,
    build_result,
)


def _write_source_37f(reports_dir: Path, **overrides: object) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "status": "READY",
        "decision": SOURCE_37F_DECISION,
        "p0_typed_confirmation_destructive_actions_closed": True,
        "p0_typed_confirmation_destructive_actions_closed_by": "4B.4.3.6.6.37F",
        "p0_hardening_closed_gap_count_after_37f": 5,
        "p0_hardening_open_gap_count_after_37f": 5,
        "phase_37_planning_only": True,
        "no_submit_p0_5_hardening_gate_locked": True,
        "typed_confirmation_guard_locked": True,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }
    payload.update(overrides)
    path = reports_dir / "4B436637F_typed_confirmation_destructive_actions_20260703T134910Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_path_closes_p0_6_without_runtime_db_mutation(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37f(reports_dir)

    result = build_result(reports_dir)

    assert result["status"] == "READY"
    assert result["decision"] == READY_DECISION
    assert result["sqlite_audit_baseline_complete"] is True
    assert result["sqlite_audit_baseline_locked"] is True
    assert result["sqlite_wal_required"] is True
    assert result["sqlite_busy_timeout_required_ms"] == 5000
    assert result["sqlite_schema_version_required"] is True
    assert result["sqlite_integrity_check_required"] is True
    assert result["sqlite_backup_hook_required"] is True
    assert result["sqlite_runtime_db_open_performed"] is False
    assert result["sqlite_runtime_db_mutation_performed"] is False
    assert result["sqlite_schema_migration_performed"] is False
    assert result["sqlite_backup_performed"] is False
    assert result["p0_sqlite_audit_baseline_closed"] is True
    assert result["p0_sqlite_audit_baseline_closed_by"] == PATCH_VERSION
    assert result["p0_hardening_closed_gap_count_after_37g"] == 6
    assert result["p0_hardening_open_gap_count_after_37g"] == 4
    assert result["no_submit_p0_6_hardening_gate_ready_count"] == result["no_submit_p0_6_hardening_gate_check_count"]


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    result = build_result(tmp_path / "reports" / "recovery")

    assert result["status"] == "NOT_READY"
    assert result["accepted_for_sqlite_audit_baseline"] is False
    assert "missing_source_37f_ready_report" in result["errors"]
    assert result["p0_sqlite_audit_baseline_closed"] is True
    assert result["no_submit_p0_6_hardening_gate_locked"] is False


def test_source_safety_violation_is_not_ready(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37f(reports_dir, network_request_performed=True)

    result = build_result(reports_dir)

    assert result["status"] == "NOT_READY"
    assert result["source_37f_safety_violation_count"] == 1
    assert "source_37f_safety_violations_present" in result["errors"]
    assert result["network_request_performed"] is False
    assert result["order_submit_performed"] is False


def test_source_p0_5_must_be_closed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37f(
        reports_dir,
        p0_typed_confirmation_destructive_actions_closed=False,
        p0_hardening_closed_gap_count_after_37f=4,
    )

    result = build_result(reports_dir)

    assert result["status"] == "NOT_READY"
    assert "source_37f_p0_5_not_closed" in result["errors"]
    assert "source_37f_closed_gap_count_not_5" in result["errors"]


def test_write_reports_creates_canonical_ready_report(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37f(reports_dir)

    result = build_result(reports_dir, write_reports=True)

    assert result["status"] == "READY"
    report_path = Path(str(result["report_path"]))
    assert report_path.exists()
    assert report_path.name.endswith("_ready.json")
    assert result["file_delete_performed"] is False
    assert result["report_delete_performed"] is False
