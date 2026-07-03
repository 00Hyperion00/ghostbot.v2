from __future__ import annotations

import json
from pathlib import Path

from tradebot.api_auth_destructive_endpoint_guard import (
    READY_DECISION,
    authorize_local_endpoint,
    evaluate,
)


def write_source_37d(tmp_path: Path, *, safety_violation: bool = False) -> Path:
    reports = tmp_path / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_3_LOCKED",
        "p0_strict_config_unknown_key_fail_closed": True,
        "p0_strict_config_unknown_key_fail_closed_by": "4B.4.3.6.6.37D",
        "p0_hardening_closed_gap_count_after_37d": 3,
        "p0_hardening_open_gap_count_after_37d": 7,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "paper_transition_blocked": True,
        "final_safety_violations": ["BAD"] if safety_violation else [],
    }
    path = reports / "4B436637D_strict_config_unknown_key_fail_closed_20260703T132727Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_authorize_local_endpoint_deny_by_default() -> None:
    safe = authorize_local_endpoint("GET", "/health", token_present=False, token_valid=False)
    missing = authorize_local_endpoint("POST", "/api/force-trade", token_present=False, token_valid=False)
    invalid = authorize_local_endpoint("POST", "/api/reload-config", token_present=True, token_valid=False)
    valid_no_submit = authorize_local_endpoint("POST", "/api/runtime-overlay/activate", token_present=True, token_valid=True)
    assert safe["result"] == "ALLOW_READ_ONLY"
    assert missing["result"] == "DENY_LOCAL_TOKEN_REQUIRED"
    assert invalid["result"] == "DENY_LOCAL_TOKEN_INVALID"
    assert valid_no_submit["result"] == "AUTH_PASSED_EXECUTION_DENIED_NO_SUBMIT"
    assert valid_no_submit["runtime_execution_allowed"] is False


def test_ready_with_clean_source_37d(tmp_path: Path) -> None:
    write_source_37d(tmp_path)
    payload = evaluate(tmp_path)
    assert payload["status"] == "READY"
    assert payload["decision"] == READY_DECISION
    assert payload["local_token_requirement_locked"] is True
    assert payload["destructive_endpoint_guard_locked"] is True
    assert payload["destructive_endpoint_probe_count"] == payload["destructive_endpoint_probe_passed_count"]
    assert payload["p0_api_auth_destructive_endpoint_guard_closed"] is True
    assert payload["p0_hardening_closed_gap_count_after_37e"] == 4
    assert payload["p0_hardening_open_gap_count_after_37e"] == 6
    assert payload["no_submit_p0_4_hardening_gate_ready_count"] == payload["no_submit_p0_4_hardening_gate_check_count"]
    assert payload["network_submit_allowed"] is False
    assert payload["order_submit_performed"] is False


def test_not_ready_without_source_37d(tmp_path: Path) -> None:
    payload = evaluate(tmp_path)
    assert payload["status"] == "NOT_READY"
    assert payload["accepted_for_api_auth_destructive_endpoint_guard"] is False
    assert "SOURCE_37D_READY_REPORT_MISSING" in payload["errors"]


def test_not_ready_if_source_37d_has_safety_violation(tmp_path: Path) -> None:
    write_source_37d(tmp_path, safety_violation=True)
    payload = evaluate(tmp_path)
    assert payload["status"] == "NOT_READY"
    assert payload["source_37d_safety_violation_count"] == 1


def test_run_script_writes_reports_without_runtime_mutation(tmp_path: Path) -> None:
    write_source_37d(tmp_path)
    reports = tmp_path / "reports" / "recovery"
    payload = evaluate(tmp_path, reports_dir=reports, write_reports=True)
    assert payload["status"] == "READY"
    assert Path(payload["report_path"]).exists()
    assert Path(payload["local_token_requirement_path"]).exists()
    assert Path(payload["destructive_endpoint_guard_path"]).exists()
    assert payload["api_route_mutation_performed"] is False
    assert payload["token_secret_written"] is False
    assert payload["transition_to_next_phase_performed"] is False
