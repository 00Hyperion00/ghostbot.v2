from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_phase40_common import PHASE_SPECS, evaluate_bundle


def test_phase40_bundle_ready_with_seeded_39g_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    reports_dir.mkdir(parents=True)
    source = {
        "ok": True,
        "status": "READY",
        "patch_id": "4B436639G",
        "patch_version": "4B.4.3.6.6.39G",
        "decision": "PAPER_SANDBOX_RUNTIME_TRANSITION_CLOSURE_READY_RUNTIME_TRANSITION_CLOSED_PAPER_RUNTIME_NOT_STARTED_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED",
        "final_safety_violation_count": 0,
        "runtime_process_started": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_start_performed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
    }
    (reports_dir / "4B436639G_seed_ready.json").write_text(json.dumps(source), encoding="utf-8")

    result = evaluate_bundle(reports_dir=reports_dir, write_reports=False)

    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["phase_count"] == len(PHASE_SPECS) == 9
    assert result["phase_ready_count"] == 9
    assert result["runtime_start_command_executed"] is False
    assert result["runtime_process_started"] is False
    assert result["paper_order_submit_performed"] is False
    assert result["network_order_submit_performed"] is False
    assert result["approved_for_live_real"] is False
    assert result["approved_for_exchange_submit"] is False
    assert result["exchange_submit_performed"] is False
    assert result["next_phase_unlock_allowed"] is False
    assert result["final_safety_violation_count"] == 0
