from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tradebot.public_observation_evidence_closure import evaluate_public_observation_evidence_closure


def _init_repo_with_tags(root: Path, tags: list[str]) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "seed.txt").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "seed", "-q"], cwd=root, check=True)
    for tag in tags:
        subprocess.run(["git", "tag", tag], cwd=root, check=True)


def _write_source_36e(root: Path, *, ready: bool = True, safety_violation: bool = False) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "PUBLIC_OBSERVATION_NETWORK_OFF_EXECUTION_PACKAGE_READY_NO_NETWORK_DRY_RUN_EVIDENCE_SEALED",
        "source_36d_complete": True,
        "phase_35_closed": True,
        "phase_36_planning_only": True,
        "token_presence_audit_complete": True,
        "token_presence_audit_locked": True,
        "token_presence_audit_digest": "token-audit-digest",
        "no_network_collector_simulation_complete": True,
        "no_network_collector_simulation_locked": True,
        "no_network_collector_simulation_digest": "simulation-digest",
        "observation_execution_dry_run_evidence_seal_complete": True,
        "observation_execution_dry_run_evidence_seal_locked": True,
        "observation_execution_dry_run_evidence_seal_digest": "dry-run-seal-digest",
        "public_observation_network_off_execution_package_ready": True,
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
        "public_observation_network_off_execution_package_executed": False,
        "public_data_fetch_adapter_executed": False,
        "network_request_performed": False,
        "network_request_allowed_now": False,
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
        "operator_observation_token_consumed": False,
        "operator_observation_token_validated": False,
        "operator_observation_authorization_unlocked": False,
        "operator_observation_token_present": False,
        "observation_dry_run_evidence_unsealed": False,
        "simulated_approval_performed": False,
    }
    path = reports / "4B436636E_public_observation_network_off_execution_package_20260703T120429Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_36e_ready_and_tags_present(tmp_path: Path) -> None:
    _init_repo_with_tags(tmp_path, [
        "4B.4.3.6.6.36A",
        "4B.4.3.6.6.36B",
        "4B.4.3.6.6.36C",
        "4B.4.3.6.6.36D",
        "4B.4.3.6.6.36E",
    ])
    _write_source_36e(tmp_path)
    result = evaluate_public_observation_evidence_closure(tmp_path, tmp_path / "reports" / "recovery")

    assert result["status"] == "READY"
    assert result["source_36e_complete"] is True
    assert result["phase_36_tag_audit_complete"] is True
    assert result["phase_36_missing_tag_count"] == 0
    assert result["network_off_evidence_digest_lock_complete"] is True
    assert result["network_off_evidence_digest_item_count"] == 4
    assert result["no_submit_phase_36_interim_closure_complete"] is True
    assert result["phase_36_interim_closed"] is True
    assert result["phase_36_final_closed"] is False
    assert result["next_phase_unlock_allowed"] is False
    assert result["order_submit_performed"] is False


def test_not_ready_when_source_36e_report_missing(tmp_path: Path) -> None:
    _init_repo_with_tags(tmp_path, ["4B.4.3.6.6.36A"])
    result = evaluate_public_observation_evidence_closure(tmp_path, tmp_path / "reports" / "recovery")

    assert result["status"] == "NOT_READY"
    assert result["source_36e_complete"] is False
    assert result["phase_36_tag_audit_complete"] is False
    assert result["network_off_evidence_digest_lock_complete"] is False
    assert result["paper_transition_ready"] is False
    assert result["exchange_submit_allowed"] is False


def test_not_ready_when_36e_tag_missing(tmp_path: Path) -> None:
    _init_repo_with_tags(tmp_path, [
        "4B.4.3.6.6.36A",
        "4B.4.3.6.6.36B",
        "4B.4.3.6.6.36C",
        "4B.4.3.6.6.36D",
    ])
    _write_source_36e(tmp_path)
    result = evaluate_public_observation_evidence_closure(tmp_path, tmp_path / "reports" / "recovery")

    assert result["status"] == "NOT_READY"
    assert result["source_36e_complete"] is True
    assert result["phase_36_tag_audit_complete"] is False
    assert result["phase_36_missing_tag_count"] == 1
    assert "4B.4.3.6.6.36E" in result["phase_36_missing_tags"]
    assert result["phase_36_interim_closed"] is False
    assert result["next_phase_unlock_performed"] is False


def test_not_ready_when_source_36e_has_safety_violation(tmp_path: Path) -> None:
    _init_repo_with_tags(tmp_path, [
        "4B.4.3.6.6.36A",
        "4B.4.3.6.6.36B",
        "4B.4.3.6.6.36C",
        "4B.4.3.6.6.36D",
        "4B.4.3.6.6.36E",
    ])
    _write_source_36e(tmp_path, safety_violation=True)
    result = evaluate_public_observation_evidence_closure(tmp_path, tmp_path / "reports" / "recovery")

    assert result["status"] == "NOT_READY"
    assert result["source_36e_complete"] is False
    assert result["source_36e_safety_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_36e_safety_violations"]
    assert result["phase_36_interim_closed"] is False
    assert result["runtime_evidence_collection_performed"] is False
