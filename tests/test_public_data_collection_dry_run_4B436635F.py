from __future__ import annotations

import json
from pathlib import Path

from tradebot.public_data_collection_dry_run import evaluate


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def source_35e_ready() -> dict:
    return {
        "status": "READY",
        "decision": "DRY_RUN_COLLECTION_AUTHORIZATION_READY_NO_SUBMIT_COLLECTION_SEAL_LOCKED",
        "no_submit_collection_seal_complete": True,
        "no_submit_collection_seal_locked": True,
        "operator_collection_token_ledger_complete": True,
        "public_data_dry_run_authorization_complete": True,
        "operator_collection_token_present": False,
        "operator_collection_token_valid": False,
        "public_data_dry_run_authorized": False,
        "phase_34_closed": True,
        "no_submit_collection_seal_digest": "seal-digest",
        "public_data_dry_run_authorization_digest": "auth-digest",
        "operator_collection_token_ledger_digest": "token-digest",
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "order_submit_performed": False,
    }


def test_ready_without_execution(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_json(reports / "4B436635E_dry_run_collection_authorization_20260703T000000Z_ready.json", source_35e_ready())

    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "READY"
    assert result["source_35e_complete"] is True
    assert result["collection_token_template_complete"] is True
    assert result["collection_token_template_is_not_authorization"] is True
    assert result["public_market_data_scope_freeze_complete"] is True
    assert result["public_market_data_scope_frozen"] is True
    assert result["no_submit_dry_run_collector_guard_complete"] is True
    assert result["no_submit_dry_run_collector_guard_locked"] is True
    assert result["dry_run_collector_executed"] is False
    assert result["public_market_data_collection_performed"] is False
    assert result["private_api_access_allowed"] is False
    assert result["order_submit_performed"] is False
    assert result["next_phase_unlock_allowed"] is False


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["source_35e_complete"] is False
    assert result["source_35e_status"] == "SOURCE_35E_REPORT_MISSING"
    assert result["order_submit_performed"] is False


def test_source_safety_violation_blocks_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    bad = source_35e_ready()
    bad["exchange_submit_allowed"] = True
    write_json(reports / "4B436635E_dry_run_collection_authorization_20260703T000000Z_ready.json", bad)

    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["source_35e_complete"] is False
    assert result["source_35e_safety_violation_count"] == 1
    assert "exchange_submit_allowed" in result["source_35e_safety_violations"]
    assert result["exchange_submit_allowed"] is False
