from __future__ import annotations

import json
from pathlib import Path

from tradebot.report_commit_policy import (
    READY_DECISION,
    build_report,
    is_commit_whitelisted,
    validate_report_provenance,
)


def write_source_37i(repo_root: Path) -> None:
    reports = repo_root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "FEE_SLIPPAGE_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_8_LOCKED",
        "p0_fee_slippage_baseline_closed": True,
        "p0_fee_slippage_baseline_closed_by": "4B.4.3.6.6.37I",
        "p0_hardening_closed_gap_count_after_37i": 8,
        "p0_hardening_open_gap_count_after_37i": 2,
        "phase_37_planning_only": True,
        "no_submit_p0_8_hardening_gate_locked": True,
        "fee_slippage_baseline_locked": True,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "order_submit_performed": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "paper_transition_unblocked": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "trading_action_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "git_commit_performed": False,
        "git_add_performed": False,
        "git_tag_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
    }
    (reports / "4B436637I_fee_slippage_baseline_20260703T000000Z_ready.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_report_ready_closes_only_p0_9(tmp_path: Path) -> None:
    write_source_37i(tmp_path)
    report = build_report(tmp_path)
    assert report["ok"] is True
    assert report["decision"] == READY_DECISION
    assert report["p0_report_commit_policy_closed"] is True
    assert report["p0_hardening_closed_gap_count_after_37j"] == 9
    assert report["p0_hardening_open_gap_count_after_37j"] == 1
    assert report["p0_hardening_complete"] is False
    assert report["next_phase_unlock_allowed"] is False


def test_commit_whitelist_accepts_only_canonical_patch_and_37j_reports() -> None:
    assert is_commit_whitelisted("src/tradebot/report_commit_policy.py") is True
    assert is_commit_whitelisted("reports/recovery/4B436637J_report_commit_policy_20260703T000000Z_ready.json") is True
    assert is_commit_whitelisted("tools/_patch_backup_4B436637I/file.py") is False
    assert is_commit_whitelisted("runtime/locks/tradebot_runtime.lock") is False
    assert is_commit_whitelisted("config.local.yaml") is False


def test_report_provenance_fails_closed_when_missing_digest() -> None:
    valid = {
        "patch_id": "4B436637J",
        "patch_version": "4B.4.3.6.6.37J",
        "patch_name": "Report Commit Policy",
        "status": "READY",
        "decision": READY_DECISION,
        "source_report": "reports/recovery/source.json",
        "generated_at_utc": "1970-01-01T00:00:00Z",
        "report_digest": "0" * 64,
    }
    invalid = {key: value for key, value in valid.items() if key != "report_digest"}
    assert validate_report_provenance(valid)["valid"] is True
    assert validate_report_provenance(invalid)["valid"] is False


def test_no_git_or_report_mutation_flags(tmp_path: Path) -> None:
    write_source_37i(tmp_path)
    report = build_report(tmp_path)
    assert report["git_add_performed"] is False
    assert report["git_commit_performed"] is False
    assert report["git_tag_performed"] is False
    assert report["report_delete_performed"] is False
    assert report["report_move_performed"] is False
    assert report["deduplication_action_performed"] is False
    assert report["historical_report_mutation_performed"] is False


def test_run_writes_expected_report_files(tmp_path: Path) -> None:
    write_source_37i(tmp_path)
    reports_dir = tmp_path / "reports" / "recovery"
    report = build_report(tmp_path, write_reports=True, reports_dir=reports_dir)
    assert report["ok"] is True
    for key in [
        "canonical_evidence_selection_path",
        "commit_whitelist_path",
        "report_provenance_guard_path",
        "report_commit_policy_probe_path",
        "p0_gap_closure_delta_path",
        "no_submit_p0_9_hardening_gate_path",
        "report_path",
    ]:
        assert Path(report[key]).exists(), key
