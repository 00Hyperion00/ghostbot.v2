from __future__ import annotations

import json
from pathlib import Path

from tradebot.install_contract_alignment import (
    READY_DECISION,
    apply_install_contract_alignment,
    evaluate_install_contract_alignment,
)


def _write_source_37a(root: Path, *, ready: bool = True, safety_violation: bool = False) -> None:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "POST_PHASE_36_PRODUCTION_READINESS_REBASELINE_READY_NO_SUBMIT_37A_PLANNING_GATE_LOCKED",
        "source_36g_complete": True,
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "production_readiness_rebaseline_ready": True,
        "p0_hardening_gap_matrix_complete": True,
        "p0_hardening_open_gap_count": 10,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "evidence_collection_started": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "http_request_performed": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "order_submit_performed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "private_account_read_performed": False,
        "private_api_access_allowed": False,
        "public_market_data_collection_performed": safety_violation,
        "public_observation_execution_performed": False,
        "reload_performed": False,
        "report_delete_performed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_probe_performed": False,
        "signed_request_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    path = reports / "4B436637A_post_phase_36_production_readiness_rebaseline_20260703T122436Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_install_files(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """
[project]
name = "tradebot"
version = "0.1.0"
dependencies = [
  "fastapi>=0.110",
  "pydantic>=2.6",
  "python-binance>=1.0",
  "xgboost>=2.0",
]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# TradeBot\n\nInstall: `pip install -r requirements.txt`\n", encoding="utf-8")
    (root / "run_dashboard.ps1").write_text("pip install -r requirements.txt\npython -m tradebot\n", encoding="utf-8")


def test_apply_alignment_then_ready(tmp_path: Path) -> None:
    _write_source_37a(tmp_path)
    _write_install_files(tmp_path)

    apply_result = apply_install_contract_alignment(tmp_path)
    assert apply_result["install_contract_mutation_performed"] is True
    assert (tmp_path / "requirements.txt").exists()
    assert "fastapi>=0.110" in (tmp_path / "requirements.txt").read_text(encoding="utf-8")
    assert "4B436637B_INSTALL_CONTRACT_START" in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "python -m pip install -r requirements.txt" in (tmp_path / "run_dashboard.ps1").read_text(encoding="utf-8")

    result = evaluate_install_contract_alignment(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )
    assert result["status"] == "READY"
    assert result["decision"] == READY_DECISION
    assert result["source_37a_complete"] is True
    assert result["install_contract_alignment_complete"] is True
    assert result["requirements_pyproject_aligned"] is True
    assert result["p0_install_contract_alignment_closed"] is True
    assert result["p0_hardening_closed_gap_count_after_37b"] == 1
    assert result["p0_hardening_open_gap_count_after_37b"] == 9
    assert result["no_submit_p0_1_hardening_gate_ready_count"] == 9
    assert result["paper_transition_blocked"] is True
    assert result["exchange_submit_allowed"] is False
    assert result["network_request_performed"] is False


def test_not_ready_when_source_37a_missing(tmp_path: Path) -> None:
    _write_install_files(tmp_path)
    apply_install_contract_alignment(tmp_path)
    result = evaluate_install_contract_alignment(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )
    assert result["status"] == "NOT_READY"
    assert result["source_37a_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False
    assert result["paper_transition_ready"] is False


def test_not_ready_when_requirements_not_aligned(tmp_path: Path) -> None:
    _write_source_37a(tmp_path)
    _write_install_files(tmp_path)
    (tmp_path / "requirements.txt").write_text("fastapi>=0.110\n", encoding="utf-8")
    result = evaluate_install_contract_alignment(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )
    assert result["status"] == "NOT_READY"
    assert result["install_contract_alignment_complete"] is False
    assert result["requirements_pyproject_aligned"] is False
    assert result["p0_install_contract_alignment_closed"] is False
    assert result["order_submit_performed"] is False


def test_not_ready_when_source_has_safety_violation(tmp_path: Path) -> None:
    _write_source_37a(tmp_path, safety_violation=True)
    _write_install_files(tmp_path)
    apply_install_contract_alignment(tmp_path)
    result = evaluate_install_contract_alignment(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )
    assert result["status"] == "NOT_READY"
    assert result["source_37a_safety_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_37a_safety_violations"]
    assert result["network_request_performed"] is False
    assert result["exchange_submit_performed"] is False
