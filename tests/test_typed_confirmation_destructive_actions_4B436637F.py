from __future__ import annotations

import json
from pathlib import Path

from tradebot.typed_confirmation_destructive_actions import (
    READY_DECISION,
    evaluate,
    evaluate_typed_confirmation,
)


def write_source_37e(tmp_path: Path, *, safety_violation: bool = False) -> Path:
    reports = tmp_path / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_4_LOCKED",
        "p0_api_auth_destructive_endpoint_guard_closed": True,
        "p0_api_auth_destructive_endpoint_guard_closed_by": "4B.4.3.6.6.37E",
        "p0_hardening_closed_gap_count_after_37e": 4,
        "p0_hardening_open_gap_count_after_37e": 6,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "paper_transition_blocked": True,
        "api_auth_guard_locked": True,
        "local_token_requirement_locked": True,
        "final_safety_violations": ["BAD"] if safety_violation else [],
    }
    path = reports / "4B436637E_api_auth_destructive_endpoint_guard_20260703T133950Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_typed_confirmation_guard_decisions() -> None:
    missing = evaluate_typed_confirmation("force_trade", None, local_token_valid=True)
    mismatch = evaluate_typed_confirmation("force_trade", "CONFIRM RELOAD CONFIG", local_token_valid=True)
    invalid_token = evaluate_typed_confirmation("reload_config", "CONFIRM RELOAD CONFIG", local_token_valid=False)
    valid_no_submit = evaluate_typed_confirmation("train_model", "CONFIRM TRAIN MODEL", local_token_valid=True)
    assert missing["result"] == "DENY_TYPED_CONFIRMATION_REQUIRED"
    assert mismatch["result"] == "DENY_TYPED_CONFIRMATION_MISMATCH"
    assert invalid_token["result"] == "DENY_LOCAL_TOKEN_INVALID"
    assert valid_no_submit["result"] == "CONFIRMATION_PASSED_EXECUTION_DENIED_NO_SUBMIT"
    assert valid_no_submit["runtime_execution_allowed"] is False


def test_ready_with_clean_source_37e(tmp_path: Path) -> None:
    write_source_37e(tmp_path)
    payload = evaluate(tmp_path)
    assert payload["status"] == "READY"
    assert payload["decision"] == READY_DECISION
    assert payload["typed_confirmation_requirement_locked"] is True
    assert payload["typed_confirmation_guard_locked"] is True
    assert payload["typed_confirmation_probe_count"] == payload["typed_confirmation_probe_passed_count"]
    assert payload["force_trade_typed_confirmation_guarded"] is True
    assert payload["reload_typed_confirmation_guarded"] is True
    assert payload["train_typed_confirmation_guarded"] is True
    assert payload["reset_typed_confirmation_guarded"] is True
    assert payload["p0_typed_confirmation_destructive_actions_closed"] is True
    assert payload["p0_hardening_closed_gap_count_after_37f"] == 5
    assert payload["p0_hardening_open_gap_count_after_37f"] == 5
    assert payload["no_submit_p0_5_hardening_gate_ready_count"] == payload["no_submit_p0_5_hardening_gate_check_count"]
    assert payload["order_submit_performed"] is False
    assert payload["destructive_action_execution_performed"] is False


def test_not_ready_without_source_37e(tmp_path: Path) -> None:
    payload = evaluate(tmp_path)
    assert payload["status"] == "NOT_READY"
    assert payload["accepted_for_typed_confirmation_destructive_actions"] is False
    assert "SOURCE_37E_READY_REPORT_MISSING" in payload["errors"]


def test_not_ready_if_source_37e_has_safety_violation(tmp_path: Path) -> None:
    write_source_37e(tmp_path, safety_violation=True)
    payload = evaluate(tmp_path)
    assert payload["status"] == "NOT_READY"
    assert payload["source_37e_safety_violation_count"] == 1


def test_run_script_writes_reports_without_runtime_mutation(tmp_path: Path) -> None:
    write_source_37e(tmp_path)
    reports = tmp_path / "reports" / "recovery"
    payload = evaluate(tmp_path, reports_dir=reports, write_reports=True)
    assert payload["status"] == "READY"
    assert Path(payload["report_path"]).exists()
    assert Path(payload["typed_confirmation_requirement_path"]).exists()
    assert Path(payload["typed_confirmation_guard_path"]).exists()
    assert payload["api_route_mutation_performed"] is False
    assert payload["typed_confirmation_runtime_binding_performed"] is False
    assert payload["typed_confirmation_secret_written"] is False
    assert payload["transition_to_next_phase_performed"] is False
