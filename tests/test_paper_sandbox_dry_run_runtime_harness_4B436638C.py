from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_dry_run_runtime_harness import READY_DECISION, build_report


def _write_source_38b(repo: Path, **overrides: object) -> Path:
    report = {
        "patch_id": "4B436638B",
        "patch_version": "4B.4.3.6.6.38B",
        "patch_name": "Paper Sandbox Runtime Preflight",
        "status": "READY",
        "decision": "PAPER_SANDBOX_RUNTIME_PREFLIGHT_READY_PAPER_ONLY_NO_LIVE_NO_EXCHANGE_SUBMIT_NO_NETWORK_ORDER_LOCKED",
        "source_38a_status": "SOURCE_38A_READY",
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
        "paper_sandbox_runtime_preflight_complete": True,
        "paper_sandbox_runtime_preflight_locked": True,
        "paper_sandbox_runtime_preflight_ready": True,
        "paper_only_runtime_config_contract_complete": True,
        "paper_only_runtime_config_contract_locked": True,
        "approved_for_paper_sandbox_runtime_preflight": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_transition": False,
        "approved_for_paper_transition_candidate": False,
        "paper_transition_ready": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "network_order_submit_performed": False,
        "network_request_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "runtime_start_performed": False,
        "phase_38_planning_only": True,
    }
    report.update(overrides)
    out = repo / "reports" / "recovery" / "4B436638B_paper_sandbox_runtime_preflight_20260704T000000Z_ready.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report), encoding="utf-8")
    return out


def test_38c_ready_from_valid_38b_source(tmp_path: Path) -> None:
    source = _write_source_38b(tmp_path)
    report = build_report(tmp_path)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38b_status"] == "SOURCE_38B_READY"
    assert report["source_report"] == str(source)
    assert report["paper_sandbox_dry_run_runtime_harness_complete"] is True
    assert report["approved_for_paper_sandbox_dry_run_harness"] is True


def test_38c_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report["status"] == "NOT_READY"
    assert "SOURCE_38B_READY_REPORT_MISSING" in report["errors"]
    assert report["paper_runtime_start_performed"] is False
    assert report["exchange_submit_performed"] is False


def test_38c_rejects_unsafe_38b_source(tmp_path: Path) -> None:
    _write_source_38b(tmp_path, network_request_performed=True)
    report = build_report(tmp_path)
    assert report["status"] == "NOT_READY"
    assert "SOURCE_38B_REQUIRED_FALSE_MISMATCH:network_request_performed" in report["errors"]
    assert report["network_request_performed"] is False


def test_38c_local_dry_run_harness_probe_contract(tmp_path: Path) -> None:
    _write_source_38b(tmp_path)
    report = build_report(tmp_path)
    assert report["dry_run_harness_probe_complete"] is True
    assert report["dry_run_harness_probe_locked"] is True
    assert report["dry_run_harness_probe_mode"] == "LOCAL_SYNTHETIC_EVENT_LOOP_NO_RUNTIME_NO_NETWORK_ORDER"
    assert report["dry_run_harness_probe_count"] == 13
    assert report["dry_run_harness_probe_passed_count"] == 13
    assert report["dry_run_harness_synthetic_event_count"] == 5
    assert report["synthetic_event_loop_declared"] is True
    assert report["simulated_order_intent_created"] is True
    assert report["simulated_fill_ledger_created"] is True


def test_38c_no_live_no_exchange_submit_no_network_order_guard(tmp_path: Path) -> None:
    _write_source_38b(tmp_path)
    report = build_report(tmp_path)
    assert report["no_network_order_no_live_no_exchange_submit_guard_complete"] is True
    assert report["no_network_order_no_live_no_exchange_submit_guard_locked"] is True
    assert report["no_network_order_guard_rule_count"] == 8
    assert report["no_network_order_guard_ready_count"] == 8
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["network_order_submit_allowed"] is False
    assert report["network_order_submit_performed"] is False


def test_38c_valid_dry_run_does_not_start_runtime_or_order(tmp_path: Path) -> None:
    _write_source_38b(tmp_path)
    report = build_report(tmp_path)
    assert report["dry_run_runtime_harness_execution_performed"] is False
    assert report["runtime_start_performed"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["paper_order_submit_performed"] is False
    assert report["order_submit_performed"] is False
    assert report["exchange_submit_performed"] is False
    assert report["signed_request_performed"] is False
    assert report["private_api_access_allowed"] is False


def test_38c_final_gate_and_next_phase_locked(tmp_path: Path) -> None:
    _write_source_38b(tmp_path)
    report = build_report(tmp_path)
    assert report["paper_sandbox_dry_run_runtime_harness_gate_complete"] is True
    assert report["paper_sandbox_dry_run_runtime_harness_gate_locked"] is True
    assert report["paper_sandbox_dry_run_runtime_harness_gate_check_count"] == 23
    assert report["paper_sandbox_dry_run_runtime_harness_gate_ready_count"] == 23
    assert report["next_phase"] == "4B.4.3.6.6.38D"
    assert report["next_phase_unlock_allowed"] is False
    assert report["transition_to_next_phase_performed"] is False


def test_38c_write_reports(tmp_path: Path) -> None:
    _write_source_38b(tmp_path)
    reports_dir = tmp_path / "reports" / "recovery"
    report = build_report(tmp_path, reports_dir, write_reports=True)
    assert report["status"] == "READY"
    for key in (
        "local_dry_run_runtime_harness_policy_path",
        "dry_run_harness_probe_path",
        "no_network_order_no_live_no_exchange_submit_guard_path",
        "paper_sandbox_dry_run_runtime_harness_gate_path",
        "report_path",
    ):
        assert Path(str(report[key])).exists()


def test_38c_report_has_clean_safety_flags(tmp_path: Path) -> None:
    _write_source_38b(tmp_path)
    report = build_report(tmp_path)
    assert report["final_safety_violation_count"] == 0
    assert report["final_safety_violations"] == []
    assert report["paper_transition_ready"] is False
    assert report["paper_transition_unblocked"] is False
    assert report["network_request_performed"] is False
    assert report["training_performed"] is False
    assert report["reload_performed"] is False
