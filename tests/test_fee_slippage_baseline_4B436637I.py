from __future__ import annotations

import json
from pathlib import Path

from tradebot.fee_slippage_baseline import (
    BREAK_EVEN_COST_FLOOR_BPS,
    PATCH_VERSION,
    READY_DECISION,
    build_report,
    evaluate_candidate,
)


def write_source_37h(repo_root: Path) -> None:
    reports = repo_root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "RUNTIME_PROCESS_LOCK_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_7_LOCKED",
        "p0_runtime_process_lock_closed": True,
        "p0_runtime_process_lock_closed_by": "4B.4.3.6.6.37H",
        "p0_hardening_closed_gap_count_after_37h": 7,
        "p0_hardening_open_gap_count_after_37h": 3,
        "phase_37_planning_only": True,
        "no_submit_p0_7_hardening_gate_locked": True,
        "runtime_process_lock_locked": True,
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
    }
    (reports / "4B436637H_runtime_process_lock_20990101T000000Z_ready.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_build_report_ready_with_source_37h(tmp_path: Path) -> None:
    write_source_37h(tmp_path)
    report = build_report(tmp_path, write_reports=False)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_37h_status"] == "SOURCE_37H_READY"
    assert report["p0_fee_slippage_baseline_closed"] is True
    assert report["p0_fee_slippage_baseline_closed_by"] == PATCH_VERSION
    assert report["p0_hardening_closed_gap_count_after_37i"] == 8
    assert report["p0_hardening_open_gap_count_after_37i"] == 2


def test_missing_source_37h_not_ready(tmp_path: Path) -> None:
    report = build_report(tmp_path, write_reports=False)
    assert report["status"] == "NOT_READY"
    assert report["source_37h_status"] == "SOURCE_37H_READY_REPORT_MISSING"


def test_break_even_floor_components() -> None:
    assert BREAK_EVEN_COST_FLOOR_BPS == 20.0
    below = evaluate_candidate(10.0, 5.0)
    assert below["result"] == "DENY_EDGE_NOT_ABOVE_BREAK_EVEN_FLOOR"
    above = evaluate_candidate(30.0, 5.0)
    assert above["result"] == "EDGE_PASSED_EXECUTION_DENIED_NO_SUBMIT"
    assert above["runtime_execution_allowed"] is False


def test_slippage_fail_closed() -> None:
    assert evaluate_candidate(30.0, None)["result"] == "DENY_SLIPPAGE_MISSING"
    assert evaluate_candidate(30.0, 20.0)["result"] == "DENY_SLIPPAGE_OVER_MAX"


def test_run_writes_reports(tmp_path: Path) -> None:
    write_source_37h(tmp_path)
    reports_dir = tmp_path / "reports" / "recovery"
    report = build_report(tmp_path, write_reports=True, reports_dir=reports_dir)
    assert report["status"] == "READY"
    assert Path(report["report_path"]).exists()
    assert Path(report["fee_slippage_baseline_path"]).exists()
    assert Path(report["fee_slippage_probe_path"]).exists()
    assert Path(report["p0_gap_closure_delta_path"]).exists()
    assert Path(report["no_submit_p0_8_hardening_gate_path"]).exists()
