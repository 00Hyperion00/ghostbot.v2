from __future__ import annotations

import json
from pathlib import Path

from tradebot.status_conflict_resolver import check_status_conflict_resolver


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_source_33d_gate_accepts_nested_destructive_endpoint_audit(tmp_path: Path) -> None:
    recovery = tmp_path / "reports" / "recovery"
    _write_json(
        recovery / "4B436633D_runtime_safety_lockdown_20260702T105700Z_ready.json",
        {
            "status": "READY",
            "decision": "RUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED",
            "central_submit_guard_passed": True,
            "operator_action_guard_passed": True,
            "runtime_overlay_guard_passed": True,
            "destructive_endpoint_audit": {
                "complete": True,
                "destructive_endpoint_count": 52,
                "unguarded_destructive_endpoint_count": 0,
            },
            "approved_for_exchange_submit": False,
            "approved_for_live_real": False,
            "approved_for_paper_transition": False,
            "approved_for_runtime_overlay": False,
            "exchange_submit_performed": False,
            "runtime_overlay_activated": False,
            "trading_action_performed": False,
            "training_performed": False,
            "reload_performed": False,
        },
    )
    _write_json(tmp_path / "reports" / "production_hardening" / "4B436630P_demo_20260621T125234Z_not_ready.json", {"status": "READY"})
    _write_json(tmp_path / "reports" / "production_hardening" / "4B436630X_first_live_real_micro_canary_submit_request.json", {"request_id": "abc"})
    payload = check_status_conflict_resolver(project_root=tmp_path, reports_root="reports")
    assert payload["source_33d_complete"] is True
    assert payload["status"] == "READY"
    assert payload["decision"] == "STATUS_CONFLICT_RESOLVER_READY_EVIDENCE_TRIAGE_COMPLETE"


def test_source_33d_gate_rejects_unguarded_nested_audit(tmp_path: Path) -> None:
    recovery = tmp_path / "reports" / "recovery"
    _write_json(
        recovery / "4B436633D_runtime_safety_lockdown_20260702T105700Z_ready.json",
        {
            "status": "READY",
            "decision": "RUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED",
            "destructive_endpoint_audit": {
                "complete": False,
                "unguarded_destructive_endpoint_count": 1,
            },
        },
    )
    payload = check_status_conflict_resolver(project_root=tmp_path, reports_root="reports")
    assert payload["source_33d_complete"] is False
    assert payload["status"] == "NOT_READY"


def test_source_33d_gate_preserves_fail_closed_flags(tmp_path: Path) -> None:
    recovery = tmp_path / "reports" / "recovery"
    _write_json(
        recovery / "4B436633D_runtime_safety_lockdown_20260702T105700Z_ready.json",
        {
            "status": "READY",
            "decision": "RUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED",
            "runtime_safety_lockdown_complete": True,
            "unguarded_destructive_endpoint_count": 0,
            "exchange_submit_allowed": True,
        },
    )
    payload = check_status_conflict_resolver(project_root=tmp_path, reports_root="reports")
    assert payload["source_33d_complete"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["exchange_submit_performed"] is False
