from __future__ import annotations

import json
from pathlib import Path

from tradebot.runtime_process_lock import (
    PATCH_VERSION,
    READY_DECISION,
    SOURCE_37G_DECISION,
    STALE_LOCK_TTL_SECONDS,
    build_result,
    classify_lock_state,
    evaluate_runtime_start_request,
)


def _write_source_37g(reports_dir: Path, **overrides: object) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "status": "READY",
        "decision": SOURCE_37G_DECISION,
        "p0_sqlite_audit_baseline_closed": True,
        "p0_sqlite_audit_baseline_closed_by": "4B.4.3.6.6.37G",
        "p0_hardening_closed_gap_count_after_37g": 6,
        "p0_hardening_open_gap_count_after_37g": 4,
        "phase_37_planning_only": True,
        "no_submit_p0_6_hardening_gate_locked": True,
        "sqlite_audit_baseline_locked": True,
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
        "runtime_health_probe_performed": False,
        "runtime_start_performed": False,
        "runtime_process_spawn_performed": False,
        "runtime_lock_file_created": False,
        "runtime_lock_file_deleted": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }
    payload.update(overrides)
    path = reports_dir / "4B436637G_sqlite_audit_baseline_20260703T135736Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_path_closes_p0_7_without_process_or_lock_mutation(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37g(reports_dir)

    result = build_result(reports_dir)

    assert result["status"] == "READY"
    assert result["decision"] == READY_DECISION
    assert result["runtime_process_lock_complete"] is True
    assert result["runtime_process_lock_locked"] is True
    assert result["single_instance_lock_required"] is True
    assert result["runtime_lock_owner_metadata_required"] is True
    assert result["stale_lock_detection_required"] is True
    assert result["stale_lock_auto_delete_allowed"] is False
    assert result["runtime_start_denied_no_submit"] is True
    assert result["runtime_lock_file_created"] is False
    assert result["runtime_lock_file_deleted"] is False
    assert result["runtime_lock_file_mutation_performed"] is False
    assert result["runtime_process_spawn_performed"] is False
    assert result["runtime_process_kill_performed"] is False
    assert result["p0_runtime_process_lock_closed"] is True
    assert result["p0_runtime_process_lock_closed_by"] == PATCH_VERSION
    assert result["p0_hardening_closed_gap_count_after_37h"] == 7
    assert result["p0_hardening_open_gap_count_after_37h"] == 3
    assert result["no_submit_p0_7_hardening_gate_ready_count"] == result["no_submit_p0_7_hardening_gate_check_count"]


def test_lock_state_classifier_and_no_submit_start_denial() -> None:
    active = evaluate_runtime_start_request(lock_present=True, owner_alive=True, age_seconds=1)
    stale = evaluate_runtime_start_request(lock_present=True, owner_alive=False, age_seconds=STALE_LOCK_TTL_SECONDS + 1)
    absent = evaluate_runtime_start_request(lock_present=False, owner_alive=False, age_seconds=0)

    assert active["decision"] == "DENY_CONCURRENT_RUNTIME_ACTIVE_LOCK"
    assert stale["decision"] == "DENY_STALE_LOCK_OPERATOR_REVIEW_REQUIRED"
    assert stale["stale_lock_auto_delete_allowed"] is False
    assert absent["decision"] == "DENY_RUNTIME_START_NO_SUBMIT"
    assert classify_lock_state(lock_present=True, owner_alive=False, age_seconds=1) == "LOCK_HELD_OWNER_UNKNOWN_DENY_UNTIL_STALE_THRESHOLD"


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    result = build_result(tmp_path / "reports" / "recovery")

    assert result["status"] == "NOT_READY"
    assert result["accepted_for_runtime_process_lock"] is False
    assert "missing_source_37g_ready_report" in result["errors"]
    assert result["p0_runtime_process_lock_closed"] is True
    assert result["no_submit_p0_7_hardening_gate_locked"] is False


def test_source_safety_violation_is_not_ready(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37g(reports_dir, runtime_start_performed=True)

    result = build_result(reports_dir)

    assert result["status"] == "NOT_READY"
    assert result["source_37g_safety_violation_count"] == 1
    assert "source_37g_safety_violations_present" in result["errors"]
    assert result["runtime_start_performed"] is False
    assert result["order_submit_performed"] is False


def test_source_p0_6_must_be_closed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37g(
        reports_dir,
        p0_sqlite_audit_baseline_closed=False,
        p0_hardening_closed_gap_count_after_37g=5,
    )

    result = build_result(reports_dir)

    assert result["status"] == "NOT_READY"
    assert "source_37g_p0_6_not_closed" in result["errors"]
    assert "source_37g_closed_gap_count_not_6" in result["errors"]


def test_write_reports_creates_canonical_ready_report(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _write_source_37g(reports_dir)

    result = build_result(reports_dir, write_reports=True)

    assert result["status"] == "READY"
    report_path = Path(str(result["report_path"]))
    assert report_path.exists()
    assert report_path.name.endswith("_ready.json")
    assert Path(str(result["runtime_process_lock_baseline_path"])).exists()
    assert Path(str(result["runtime_process_lock_probe_path"])).exists()
    assert result["file_delete_performed"] is False
    assert result["report_delete_performed"] is False
