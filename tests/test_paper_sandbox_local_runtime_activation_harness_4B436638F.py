from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_local_runtime_activation_harness import (
    READY_DECISION,
    SOURCE_READY_DECISION,
    build_report,
)


def write_source_38e(tmp_path: Path, **overrides: object) -> Path:
    reports = tmp_path / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "status": "READY",
        "decision": SOURCE_READY_DECISION,
        "source_38d_status": "SOURCE_38D_READY",
        "paper_sandbox_runtime_activation_preflight_ready": True,
        "paper_sandbox_runtime_activation_preflight_locked": True,
        "typed_operator_approval_verified_for_preflight_review": True,
        "local_runtime_start_preflight_ready": True,
        "paper_transition_blocked": True,
        "approved_for_paper_transition": False,
        "runtime_start_performed": False,
        "paper_runtime_start_performed": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "source_38d_safety_violation_count": 0,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
        "next_phase_unlock_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    payload.update(overrides)
    path = reports / "4B436638E_paper_sandbox_runtime_activation_preflight_20260705T123645Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return reports


def test_ready_report_from_valid_38e_source(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path)
    report = build_report(reports)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38e_status"] == "SOURCE_38E_READY"


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "reports" / "recovery")
    assert report["ok"] is False
    assert report["status"] == "BLOCKED"
    assert report["approved_for_paper_transition"] is False
    assert report["runtime_start_performed"] is False


def test_bad_source_decision_fails_closed(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path, decision="BAD")
    report = build_report(reports)
    assert report["ok"] is False
    assert "source_decision_ready" in report["errors"]


def test_policy_is_paper_only_and_local(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path)
    report = build_report(reports)
    assert report["paper_only_local_runtime_activation_harness_complete"] is True
    assert report["paper_only_local_runtime_activation_harness_locked"] is True
    assert report["harness_rule_count"] == 12
    assert report["harness_ready_count"] == 12
    assert report["runtime_process_start_forbidden_in_38f"] is True


def test_local_session_ledger_does_not_start_runtime(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path)
    report = build_report(reports)
    assert report["local_activation_session_ledger_complete"] is True
    assert report["local_activation_session_created"] is True
    assert report["local_activation_session_process_started"] is False
    assert report["local_activation_session_runtime_binding_performed"] is False
    assert report["runtime_start_performed"] is False


def test_probe_and_gate_counts(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path)
    report = build_report(reports)
    assert report["local_runtime_activation_harness_probe_count"] == 16
    assert report["local_runtime_activation_harness_probe_passed_count"] == 16
    assert report["paper_sandbox_local_runtime_activation_harness_gate_check_count"] == 28
    assert report["paper_sandbox_local_runtime_activation_harness_gate_ready_count"] == 28


def test_no_network_live_exchange_submit(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path)
    report = build_report(reports)
    assert report["network_order_submit_allowed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["live_environment_enabled"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["exchange_submit_performed"] is False
    assert report["signed_request_performed"] is False
    assert report["private_api_access_allowed"] is False


def test_write_reports_creates_artifacts(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path)
    report = build_report(reports, write_reports=True)
    assert report["ok"] is True
    assert report["report_path"]
    assert Path(str(report["report_path"])).exists()
    assert Path(str(report["paper_sandbox_local_runtime_activation_harness_gate_path"])).exists()


def test_next_phase_locked(tmp_path: Path) -> None:
    reports = write_source_38e(tmp_path)
    report = build_report(reports)
    assert report["next_phase"] == "4B.4.3.6.6.38G"
    assert report["next_phase_unlock_allowed"] is False
    assert report["transition_to_next_phase_performed"] is False
