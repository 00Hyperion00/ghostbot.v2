from __future__ import annotations

import json
from pathlib import Path

from tradebot.dry_run_collection_authorization import EvaluationConfig, evaluate

READY_DECISION_35D = "COLLECTION_PREFLIGHT_GATE_READY_NO_SUBMIT_EXECUTION_GUARD_LOCKED"


def write_source_35d(reports_dir: Path, **overrides: object) -> Path:
    payload: dict[str, object] = {
        "status": "READY",
        "decision": READY_DECISION_35D,
        "source_35c_complete": True,
        "public_data_permission_ledger_complete": True,
        "public_data_permission_count": 3,
        "public_data_permission_planned": True,
        "public_data_permission_granted_for_execution": False,
        "runtime_probe_dry_run_plan_complete": True,
        "runtime_probe_dry_run_count": 4,
        "no_submit_execution_guard_complete": True,
        "no_submit_execution_guard_locked": True,
        "no_submit_execution_guard_digest": "guard-digest",
        "collection_preflight_ready": True,
        "collection_preflight_executable_now": False,
        "collection_preflight_executed": False,
        "evidence_collection_started": False,
        "runtime_evidence_collection_performed": False,
        "public_market_data_collection_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "phase_34_closed": True,
        "phase_35_planning_only": True,
        "submit_boundary_relaxed": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
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
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    payload.update(overrides)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "4B436635D_collection_preflight_gate_20260703T000000Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_default_no_token_no_submit(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_35d(reports)
    result = evaluate(EvaluationConfig(project_root=tmp_path, reports_dir=reports))
    assert result["status"] == "READY"
    assert result["source_35d_complete"] is True
    assert result["operator_collection_token_ledger_complete"] is True
    assert result["operator_collection_token_present"] is False
    assert result["public_data_dry_run_authorized"] is False
    assert result["no_submit_collection_sealed"] is True
    assert result["runtime_evidence_collection_performed"] is False
    assert result["order_submit_performed"] is False
    assert result["next_phase"] == "4B.4.3.6.6.35F"


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    result = evaluate(EvaluationConfig(project_root=tmp_path, reports_dir=reports))
    assert result["status"] == "NOT_READY"
    assert result["source_35d_complete"] is False
    assert "source_35d_report_missing" in result["errors"]


def test_source_safety_violation_is_not_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_35d(reports, exchange_submit_allowed=True)
    result = evaluate(EvaluationConfig(project_root=tmp_path, reports_dir=reports))
    assert result["status"] == "NOT_READY"
    assert result["source_35d_complete"] is False
    assert any("exchange_submit_allowed" in err for err in result["errors"])
