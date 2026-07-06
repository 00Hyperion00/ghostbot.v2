from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_no_order_runtime_soak_closure import PATCH_ID, PATCH_VERSION, evaluate


def _seed_phase40_source(reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "status": "READY",
        "patch_id": "4B436640",
        "patch_version": "4B.4.3.6.6.40",
        "decision": "PHASE40_RUNTIME_START_EXECUTION_AUTHORIZATION_BUNDLE_READY_NO_RUNTIME_START_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED",
        "final_safety_violation_count": 0,
        "runtime_process_started": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_start_performed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
    }
    (reports_dir / "4B436640_seed_ready.json").write_text(json.dumps(payload), encoding="utf-8")


def test_paper_sandbox_no_order_runtime_soak_closure_4B436641I_ready_with_seeded_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _seed_phase40_source(reports_dir)
    result = evaluate(reports_dir=str(reports_dir), write_reports=False)
    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["patch_id"] == PATCH_ID
    assert result["patch_version"] == PATCH_VERSION
    assert result["runtime_start_command_executed"] is False
    assert result["runtime_start_command_execution_performed"] is False
    assert result["runtime_process_started"] is False
    assert result["paper_runtime_start_performed"] is False
    assert result["paper_order_submit_performed"] is False
    assert result["network_order_submit_performed"] is False
    assert result["approved_for_live_real"] is False
    assert result["approved_for_exchange_submit"] is False
    assert result["exchange_submit_performed"] is False
    assert result["final_safety_violation_count"] == 0
    assert result["next_phase_unlock_allowed"] is False
