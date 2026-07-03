from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.collection_preflight_gate import evaluate

READY_35C = {
    "status": "READY",
    "decision": "RUNTIME_EVIDENCE_COLLECTION_PLAN_READY_NO_SUBMIT_COLLECTION_BOUNDARY_LOCKED",
    "source_35b_complete": True,
    "phase_34_closed": True,
    "phase_35_planning_only": True,
    "evidence_source_registry_complete": True,
    "evidence_source_count": 5,
    "evidence_source_registry_digest": "registry-digest",
    "collection_runbook_matrix_complete": True,
    "collection_runbook_count": 5,
    "collection_runbook_matrix_digest": "runbook-digest",
    "collection_runbook_executed": False,
    "no_submit_collection_boundary_complete": True,
    "no_submit_collection_boundary_locked": True,
    "no_submit_collection_boundary_digest": "boundary-digest",
    "runtime_evidence_collection_plan_ready": True,
    "runtime_evidence_collection_performed": False,
    "evidence_collection_started": False,
    "public_market_data_collection_performed": False,
    "private_api_access_allowed": False,
    "private_account_read_performed": False,
    "runtime_health_probe_performed": False,
    "paper_transition_blocked": True,
    "paper_transition_unblocked": False,
    "runtime_readiness_blocker_count": 5,
    "approved_for_exchange_submit": False,
    "exchange_submit_allowed": False,
    "network_submit_allowed": False,
    "order_submit_performed": False,
    "trading_action_performed": False,
    "approved_for_paper_transition": False,
    "paper_submit_allowed": False,
    "approved_for_live_real": False,
    "live_real_submit_allowed": False,
    "approved_for_runtime_overlay": False,
    "runtime_overlay_allowed": False,
    "runtime_overlay_activated": False,
    "training_performed": False,
    "reload_performed": False,
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
    "runtime_readiness_unlock_performed": False,
    "paper_transition_approval_performed": False,
    "paper_environment_enabled": False,
    "live_environment_enabled": False,
}


def write_source(tmp_path: Path, data: dict) -> Path:
    reports = tmp_path / "reports" / "recovery"
    reports.mkdir(parents=True)
    path = reports / "4B436635C_runtime_evidence_collection_plan_20260703T000000Z_ready.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return reports


def test_ready_source_produces_preflight_gate_ready(tmp_path: Path) -> None:
    reports = write_source(tmp_path, READY_35C)
    result = evaluate(tmp_path, reports, write_reports=True)
    assert result["status"] == "READY"
    assert result["source_35c_complete"] is True
    assert result["public_data_permission_ledger_complete"] is True
    assert result["public_data_permission_granted_for_execution"] is False
    assert result["runtime_probe_dry_run_plan_complete"] is True
    assert result["runtime_probe_performed"] is False
    assert result["no_submit_execution_guard_locked"] is True
    assert result["runtime_evidence_collection_performed"] is False
    assert result["next_phase_unlock_allowed"] is False
    assert result["report_path"] is not None


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    reports.mkdir(parents=True)
    result = evaluate(tmp_path, reports, write_reports=False)
    assert result["status"] == "NOT_READY"
    assert result["source_35c_complete"] is False
    assert "SOURCE_35C_READY_REPORT_MISSING" in result["errors"]


def test_safety_violation_blocks_readiness(tmp_path: Path) -> None:
    unsafe = dict(READY_35C)
    unsafe["exchange_submit_allowed"] = True
    reports = write_source(tmp_path, unsafe)
    result = evaluate(tmp_path, reports, write_reports=False)
    assert result["status"] == "NOT_READY"
    assert "exchange_submit_allowed" in result["source_35c_safety_violations"]
    assert result["next_phase_unlock_allowed"] is False
    assert result["order_submit_performed"] is False
