from __future__ import annotations

import json
from pathlib import Path

from tradebot.dry_run_collector_closure import evaluate


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def source_35f_ready() -> dict:
    return {
        "status": "READY",
        "decision": "PUBLIC_DATA_COLLECTION_DRY_RUN_READY_NO_SUBMIT_COLLECTOR_GUARD_LOCKED",
        "collection_token_template_complete": True,
        "collection_token_template_is_not_authorization": True,
        "collection_token_template_digest": "token-template-digest",
        "collection_token_present": False,
        "collection_token_valid": False,
        "public_market_data_scope_freeze_complete": True,
        "public_market_data_scope_frozen": True,
        "public_market_data_scope_count": 5,
        "public_market_data_scope_freeze_digest": "scope-freeze-digest",
        "public_data_collection_scope_ready": True,
        "public_data_collection_allowed_now": False,
        "no_submit_dry_run_collector_guard_complete": True,
        "no_submit_dry_run_collector_guard_locked": True,
        "no_submit_dry_run_collector_guard_digest": "guard-digest",
        "dry_run_collector_executed": False,
        "collector_guard_relaxed": False,
        "public_market_data_collection_performed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "collection_preflight_executed": False,
        "collection_runbook_executed": False,
        "collection_authorization_unlocked": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "phase_34_closed": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
    }


def test_ready_without_execution(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_json(reports / "4B436635F_public_data_collection_dry_run_20260703T000000Z_ready.json", source_35f_ready())

    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "READY"
    assert result["source_35f_complete"] is True
    assert result["collector_scope_digest_ledger_complete"] is True
    assert result["no_execution_proof_ledger_complete"] is True
    assert result["no_execution_confirmed"] is True
    assert result["paper_blocker_carry_forward_complete"] is True
    assert result["paper_transition_blocked"] is True
    assert result["dry_run_collector_executed"] is False
    assert result["public_market_data_collection_performed"] is False
    assert result["order_submit_performed"] is False
    assert result["next_phase_unlock_allowed"] is False


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["source_35f_complete"] is False
    assert result["source_35f_status"] == "SOURCE_35F_REPORT_MISSING"
    assert result["order_submit_performed"] is False


def test_execution_violation_blocks_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    bad = source_35f_ready()
    bad["public_market_data_collection_performed"] = True
    write_json(reports / "4B436635F_public_data_collection_dry_run_20260703T000000Z_ready.json", bad)

    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["source_35f_complete"] is False
    assert result["source_35f_execution_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_35f_execution_violations"]
    assert result["public_market_data_collection_performed"] is False
