from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_phase43_common import evaluate_bundle


def _seed_phase42_source(reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "status": "READY",
        "patch_id": "4B436642",
        "patch_version": "4B.4.3.6.6.42",
        "decision": "PHASE42_NO_ORDER_SOAK_EXECUTION_AUTHORIZATION_BUNDLE_READY_SOAK_EXECUTION_NOT_PERFORMED_BY_PATCH_NO_PAPER_ORDER_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED",
        "final_safety_violation_count": 0,
        "runtime_started_by_patch": False,
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
    (reports_dir / "4B436642_seed_ready.json").write_text(json.dumps(payload), encoding="utf-8")


def test_phase43_bundle_ready_with_seeded_phase42_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    _seed_phase42_source(reports_dir)
    result = evaluate_bundle(reports_dir=str(reports_dir), write_reports=True)
    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["patch_id"] == "4B436643"
    assert result["patch_version"] == "4B.4.3.6.6.43"
    assert result["phase_count"] == 9
    assert result["phase_ready_count"] == 9
    assert result["phase_43_closed"] is True
    assert result["actual_evidence_collection_performed_by_patch"] is False
    assert result["runtime_presence_evidence_collected_by_patch"] is False
    assert result["health_evidence_collected_by_patch"] is False
    assert result["metrics_evidence_collected_by_patch"] is False
    assert result["runtime_started_by_patch"] is False
    assert result["runtime_process_started"] is False
    assert result["runtime_start_command_executed"] is False
    assert result["paper_order_submit_performed"] is False
    assert result["network_order_submit_performed"] is False
    assert result["approved_for_live_real"] is False
    assert result["approved_for_exchange_submit"] is False
    assert result["exchange_submit_performed"] is False
    assert result["final_safety_violation_count"] == 0
    assert result["next_phase"] == "4B.4.3.6.6.44A"
    assert result["next_phase_unlock_allowed"] is False
