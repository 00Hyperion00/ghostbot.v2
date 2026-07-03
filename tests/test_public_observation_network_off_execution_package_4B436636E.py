from __future__ import annotations

import json
from pathlib import Path

from tradebot.public_observation_network_off_execution_package import evaluate_public_observation_network_off_execution_package


def _write_source_36d(root: Path, *, ready: bool = True, safety_violation: bool = False) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "PUBLIC_OBSERVATION_EXECUTION_AUTHORIZATION_READY_NETWORK_OFF_NO_SUBMIT_SEALED",
        "phase_35_closed": True,
        "phase_36_planning_only": True,
        "source_36c_complete": True,
        "operator_observation_token_ledger_complete": True,
        "operator_observation_token_template_complete": True,
        "operator_observation_token_required": True,
        "operator_observation_token_present": False,
        "operator_observation_token_validated": False,
        "operator_observation_authorization_unlocked": False,
        "operator_observation_token_ledger_digest": "token-ledger-digest",
        "operator_observation_token_template_digest": "token-template-digest",
        "operator_observation_token_template": {
            "token_file": "reports/recovery/operator_observation_token_4B436636D.json",
            "required_phrase": "AUTHORIZE_PUBLIC_OBSERVATION_NETWORK_OFF_NO_SUBMIT",
            "operator_id_required": True,
            "token_ttl_sec": 900,
        },
        "network_off_safety_override_ledger_complete": True,
        "network_off_safety_override_locked": True,
        "network_off_safety_override_ledger_digest": "network-off-digest",
        "network_off_safety_override_consumed": False,
        "network_off_safety_override_relaxed": False,
        "no_submit_execution_seal_complete": True,
        "no_submit_execution_seal_locked": True,
        "no_submit_execution_seal_digest": "no-submit-seal-digest",
        "no_submit_execution_seal_relaxed": False,
        "public_observation_execution_authorization_ready": True,
        "public_observation_execution_authorized_now": False,
        "public_observation_execution_allowed_now": False,
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
        "runtime_evidence_artifact_written": False,
        "public_market_data_collection_performed": safety_violation,
        "public_observation_execution_performed": False,
        "public_observation_dry_run_collector_executed": False,
        "public_data_fetch_adapter_executed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
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
    }
    path = reports / "4B436636D_public_observation_execution_authorization_20260703T115859Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_36d_is_authorization_ready_and_token_absent(tmp_path: Path) -> None:
    _write_source_36d(tmp_path)
    result = evaluate_public_observation_network_off_execution_package(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["source_36d_complete"] is True
    assert result["token_presence_audit_complete"] is True
    assert result["operator_observation_token_present_actual"] is False
    assert result["operator_observation_token_consumed"] is False
    assert result["no_network_collector_simulation_complete"] is True
    assert result["no_network_collector_simulation_record_count"] == 4
    assert result["observation_execution_dry_run_evidence_seal_complete"] is True
    assert result["observation_execution_dry_run_evidence_seal_locked_count"] == 8
    assert result["public_observation_network_off_execution_package_ready"] is True
    assert result["network_request_performed"] is False
    assert result["http_request_performed"] is False
    assert result["signed_request_performed"] is False
    assert result["observation_artifact_written"] is False
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_blocked"] is True


def test_ready_when_token_file_is_present_but_not_consumed(tmp_path: Path) -> None:
    _write_source_36d(tmp_path)
    token_path = tmp_path / "reports" / "recovery" / "operator_observation_token_4B436636D.json"
    token_path.write_text(json.dumps({"operator_id": "unit-test", "phrase": "AUTHORIZE_PUBLIC_OBSERVATION_NETWORK_OFF_NO_SUBMIT"}), encoding="utf-8")
    result = evaluate_public_observation_network_off_execution_package(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["operator_observation_token_present_actual"] is True
    assert result["operator_observation_token_payload_parse_ok"] is True
    assert result["operator_observation_token_payload_digest"]
    assert result["operator_observation_token_consumed"] is False
    assert result["operator_observation_token_validated"] is False
    assert result["operator_observation_authorization_unlocked"] is False
    assert result["network_request_allowed_now"] is False


def test_not_ready_when_source_36d_report_is_missing(tmp_path: Path) -> None:
    result = evaluate_public_observation_network_off_execution_package(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36d_complete"] is False
    assert result["token_presence_audit_complete"] is False
    assert result["no_network_collector_simulation_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False
    assert result["exchange_submit_allowed"] is False
    assert result["paper_transition_ready"] is False


def test_not_ready_when_source_36d_has_execution_violation(tmp_path: Path) -> None:
    _write_source_36d(tmp_path, safety_violation=True)
    result = evaluate_public_observation_network_off_execution_package(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36d_complete"] is False
    assert result["source_36d_safety_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_36d_safety_violations"]
    assert result["network_request_performed"] is False
    assert result["observation_artifact_written"] is False
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_unblocked"] is False
