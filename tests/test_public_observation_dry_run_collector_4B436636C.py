from __future__ import annotations

import json
from pathlib import Path

from tradebot.public_observation_dry_run_collector import evaluate_public_observation_dry_run_collector


def _write_source_36b(root: Path, *, ready: bool = True, safety_violation: bool = False) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    endpoint_items = [
        {
            "contract_id": "public_exchange_info_snapshot",
            "endpoint_family": "public_exchange_metadata",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
        {
            "contract_id": "public_klines_observation",
            "endpoint_family": "public_klines",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
        {
            "contract_id": "public_mark_price_observation",
            "endpoint_family": "public_mark_price",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
        {
            "contract_id": "public_book_ticker_observation",
            "endpoint_family": "public_book_ticker",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
    ]
    schema_fields = [
        {"field": "patch_version", "required": True, "type": "string"},
        {"field": "observation_scope_id", "required": True, "type": "string"},
        {"field": "symbol", "required": True, "type": "string"},
        {"field": "timeframe", "required": False, "type": "string|null"},
        {"field": "captured_at_utc", "required": True, "type": "string"},
        {"field": "source_endpoint_family", "required": True, "type": "string"},
        {"field": "payload_digest", "required": True, "type": "sha256_hex"},
        {"field": "submit_flags", "required": True, "type": "object"},
        {"field": "validation_errors", "required": True, "type": "array"},
    ]
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "PUBLIC_OBSERVATION_EXECUTION_PREFLIGHT_READY_NO_SUBMIT_EXECUTION_READINESS_GATE_LOCKED",
        "phase_35_closed": True,
        "phase_36_planning_only": True,
        "source_36a_complete": True,
        "read_only_public_endpoint_contract_complete": True,
        "read_only_public_endpoint_contract_locked": True,
        "read_only_public_endpoint_contract_digest": "endpoint-contract-digest",
        "read_only_public_endpoint_contract_items": endpoint_items,
        "read_only_public_endpoint_count": 4,
        "observation_artifact_schema_complete": True,
        "observation_artifact_schema_locked": True,
        "observation_artifact_schema_version": "1.0",
        "observation_artifact_schema_digest": "schema-digest",
        "observation_artifact_schema_fields": schema_fields,
        "no_submit_execution_readiness_gate_complete": True,
        "no_submit_execution_readiness_gate_locked": True,
        "no_submit_execution_readiness_gate_digest": "gate-digest",
        "execution_readiness_ready_count": 6,
        "public_observation_execution_preflight_ready": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "public_market_data_collection_performed": safety_violation,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "destructive_cleanup_performed": False,
        "deduplication_action_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "paper_transition_approval_performed": False,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "public_data_collection_allowed_now": False,
        "public_data_observation_allowed_now": False,
        "public_endpoint_execution_allowed_now": False,
        "public_observation_execution_allowed_now": False,
        "public_observation_execution_performed": False,
        "public_observation_preflight_executed": False,
        "observation_artifact_written": False,
        "observation_artifact_validation_performed": False,
        "read_only_endpoint_contract_relaxed": False,
        "observation_artifact_schema_relaxed": False,
        "execution_readiness_gate_relaxed": False,
    }
    path = reports / "4B436636B_public_observation_execution_preflight_20260703T114002Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_36b_is_preflight_ready(tmp_path: Path) -> None:
    _write_source_36b(tmp_path)
    result = evaluate_public_observation_dry_run_collector(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["source_36b_complete"] is True
    assert result["read_only_public_data_fetch_adapter_complete"] is True
    assert result["read_only_public_data_fetch_adapter_locked"] is True
    assert result["read_only_public_data_fetch_adapter_item_count"] == 4
    assert result["observation_artifact_writer_complete"] is True
    assert result["observation_artifact_writer_locked"] is True
    assert result["observation_artifact_candidate_count"] == 4
    assert result["no_submit_runtime_evidence_guard_complete"] is True
    assert result["runtime_evidence_guard_ready_count"] == 7
    assert result["public_observation_dry_run_collector_ready"] is True
    assert result["public_observation_dry_run_collector_executable_now"] is False
    assert result["network_request_performed"] is False
    assert result["observation_artifact_written"] is False
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_blocked"] is True


def test_not_ready_when_source_36b_report_is_missing(tmp_path: Path) -> None:
    result = evaluate_public_observation_dry_run_collector(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36b_complete"] is False
    assert result["read_only_public_data_fetch_adapter_complete"] is False
    assert result["observation_artifact_writer_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False
    assert result["exchange_submit_allowed"] is False
    assert result["paper_transition_ready"] is False


def test_not_ready_when_source_36b_has_execution_violation(tmp_path: Path) -> None:
    _write_source_36b(tmp_path, safety_violation=True)
    result = evaluate_public_observation_dry_run_collector(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36b_complete"] is False
    assert result["source_36b_safety_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_36b_safety_violations"]
    assert result["network_request_performed"] is False
    assert result["observation_artifact_written"] is False
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_unblocked"] is False
