from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.paper_sandbox_runtime_preflight import (
    CANONICAL_PAPER_ONLY_CONFIG,
    READY_DECISION,
    SOURCE_DECISION_38A,
    build_report,
    evaluate_paper_only_config,
    run_preflight_probes,
)


def _write_source_38a(tmp_path: Path) -> Path:
    reports = tmp_path / "reports" / "recovery"
    reports.mkdir(parents=True)
    payload = {
        "patch_id": "4B436638A",
        "patch_version": "4B.4.3.6.6.38A",
        "patch_name": "Paper Transition Readiness Review",
        "status": "READY",
        "decision": SOURCE_DECISION_38A,
        "paper_transition_readiness_review_complete": True,
        "paper_transition_readiness_review_locked": True,
        "paper_transition_review_ready": True,
        "approved_for_paper_transition_review": True,
        "source_37l_status": "SOURCE_37L_READY",
        "phase_37_final_closed": True,
        "paper_transition_blocked": True,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_start_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
        "phase_38_planning_only": True,
    }
    path = reports / "4B436638A_paper_transition_readiness_review_20260704T083737Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_evaluate_valid_paper_config_denies_runtime_start() -> None:
    result = evaluate_paper_only_config(dict(CANONICAL_PAPER_ONLY_CONFIG))
    assert result == "PAPER_ONLY_CONFIG_VALID_RUNTIME_START_DENIED_NO_SUBMIT"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("environment_mode", "live", "DENY_PAPER_MODE_REQUIRED"),
        ("paper_environment_enabled", False, "DENY_PAPER_ENVIRONMENT_REQUIRED"),
        ("live_environment_enabled", True, "DENY_LIVE_ENVIRONMENT_ENABLED"),
        ("exchange_submit_allowed", True, "DENY_EXCHANGE_SUBMIT_ENABLED"),
        ("network_order_submit_allowed", True, "DENY_NETWORK_ORDER_SUBMIT_ENABLED"),
        ("signed_request_allowed", True, "DENY_SIGNED_REQUEST_ENABLED"),
        ("private_api_access_allowed", True, "DENY_PRIVATE_API_ACCESS_ENABLED"),
        ("runtime_overlay_allowed", True, "DENY_RUNTIME_OVERLAY_ENABLED"),
        ("training_allowed", True, "DENY_TRAINING_ENABLED"),
        ("reload_allowed", True, "DENY_RELOAD_ENABLED"),
    ],
)
def test_evaluate_paper_config_fail_closed(field: str, value: object, expected: str) -> None:
    config = dict(CANONICAL_PAPER_ONLY_CONFIG)
    config[field] = value
    assert evaluate_paper_only_config(config) == expected


def test_preflight_probes_all_pass() -> None:
    probes = run_preflight_probes()
    assert len(probes) == 11
    assert all(probe.passed for probe in probes)
    assert all(not probe.runtime_start_allowed for probe in probes)
    assert all(not probe.order_submit_allowed for probe in probes)


def test_build_report_ready_with_valid_source(tmp_path: Path) -> None:
    _write_source_38a(tmp_path)
    report = build_report(tmp_path, tmp_path / "reports" / "recovery", write_reports=False)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38a_status"] == "SOURCE_38A_READY"
    assert report["paper_sandbox_runtime_preflight_complete"] is True
    assert report["paper_sandbox_runtime_preflight_gate_ready_count"] == report["paper_sandbox_runtime_preflight_gate_check_count"]
    assert report["approved_for_paper_sandbox_runtime_preflight"] is True
    assert report["approved_for_paper_transition"] is False
    assert report["paper_transition_ready"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["paper_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["network_order_submit_performed"] is False
    assert report["final_safety_violation_count"] == 0


def test_build_report_not_ready_without_source(tmp_path: Path) -> None:
    report = build_report(tmp_path, tmp_path / "reports" / "recovery", write_reports=False)
    assert report["ok"] is False
    assert report["status"] == "NOT_READY"
    assert report["source_38a_status"] == "SOURCE_38A_NOT_READY"
    assert "source_38a_report_missing" in report["errors"]


def test_build_report_writes_reports(tmp_path: Path) -> None:
    _write_source_38a(tmp_path)
    report = build_report(tmp_path, tmp_path / "reports" / "recovery", write_reports=True)
    assert report["ok"] is True
    assert report["report_path"] is not None
    assert Path(report["report_path"]).exists()
    assert Path(report["paper_only_runtime_config_contract_path"]).exists()
    assert Path(report["paper_sandbox_runtime_preflight_gate_path"]).exists()
