from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tradebot.operator_cockpit_hyp006_binding import (
    BRANCH_ID,
    FRESH_LEDGER_NAMESPACE,
    apply_hyp006_operator_cockpit_binding,
    hyp006_binding_available,
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _seed_hyp006_reports(root: Path) -> None:
    reports = root / "reports" / "hyp006_r1_canonical"
    rows = [
        {"branch_id": BRANCH_ID, "no_order_measurement_only": True, "observation_id": "HYP-006-XRPUSDT-4h-2026-06-01T000000Z", "symbol": "XRPUSDT", "timestamp_utc": "2026-06-01T00:00:00+00:00", "forward_return_bps_final_short_probe": 110.0, "spread_slippage_proxy_bps": 4.1},
        {"branch_id": BRANCH_ID, "no_order_measurement_only": True, "observation_id": "HYP-006-BTCUSDT-4h-2026-06-01T040000Z", "symbol": "BTCUSDT", "timestamp_utc": "2026-06-01T04:00:00+00:00", "forward_return_bps_final_short_probe": -25.0, "spread_slippage_proxy_bps": 6.5},
        {"branch_id": BRANCH_ID, "no_order_measurement_only": True, "observation_id": "HYP-006-ETHUSDT-4h-2026-06-01T080000Z", "symbol": "ETHUSDT", "timestamp_utc": "2026-06-01T08:00:00+00:00", "forward_return_bps_final_short_probe": 60.0, "spread_slippage_proxy_bps": 3.2},
    ]
    _write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260615T000000Z.jsonl", rows)
    _write_json(reports / "4B436628E_hyp006_r1_scheduler_execution_health_verify_20260615T000001Z.json", {
        "contract_version": "4B.4.3.6.6.28E",
        "decision": "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY",
        "ok": True,
        "scheduler_task_health": {"task_name": "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection", "state": "Ready", "last_task_result": 0, "number_of_missed_runs": 0},
    })
    _write_json(reports / "4B436628F_hyp006_r1_operator_cockpit_baseline_20260615T000002Z.json", {
        "contract_version": "4B.4.3.6.6.28F",
        "branch_id": BRANCH_ID,
        "ok": True,
        "decision": "HYP006_R1_SHADOW_OPERATOR_COCKPIT_BASELINE_READY",
        "baseline_summary": {"unique_observation_ids": 3, "mean_return_bps": 48.333333, "median_return_bps": 60.0, "profit_factor": 6.8, "win_rate_pct": 66.666667, "matured_count": 3, "win_count": 2, "loss_count": 1},
        "acceptance_baseline_metrics": {"sample_target": 30, "sample_progress_pct": 10.0, "acceptance_requirements_met": False},
        "dashboard_seed": {"scheduler": {"task_name": "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection", "state": "Ready", "last_task_result": 0, "number_of_missed_runs": 0}},
    })
    _write_json(reports / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260615T000003Z.json", {
        "contract_version": "4B.4.3.6.6.28G",
        "branch_id": BRANCH_ID,
        "ok": True,
        "decision": "HYP006_R1_SHADOW_SAMPLE_EXPANSION_ACCEPTANCE_TRACKING_READY",
        "approved_for_acceptance_tracking": True,
        "approved_for_acceptance_review_candidate": False,
        "blockers": ["SHADOW_SAMPLE_COUNT_BELOW_TARGET", "PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT_NOT_PRESENT"],
        "baseline_summary": {"unique_observation_ids": 3, "mean_return_bps": 48.333333, "median_return_bps": 60.0, "profit_factor": 6.8, "win_rate_pct": 66.666667, "matured_count": 3, "win_count": 2, "loss_count": 1},
        "acceptance_tracking_metrics": {"sample_target": 30, "sample_progress_pct": 10.0, "acceptance_requirements_met": False},
    })


def test_hyp006_binding_overlays_legacy_hyp005_snapshot(tmp_path: Path) -> None:
    _seed_hyp006_reports(tmp_path)
    legacy = {
        "contract_version": "4B.4.3.6.6.26A",
        "branch_id": "HYP-005-R1",
        "fresh_ledger_namespace": "HYP005_R1",
        "model": {"status": "DISCOVERED_READ_ONLY", "file_name": "legacy-model.ubj"},
        "scheduler": {"r1_task": {"task_name": "TradeBot_HYP005_R1", "state": "Ready"}},
    }
    result = apply_hyp006_operator_cockpit_binding(legacy, tmp_path)
    assert result["branch_id"] == BRANCH_ID
    assert result["fresh_ledger_namespace"] == FRESH_LEDGER_NAMESPACE
    assert result["legacy_hyp005_panel_suppressed"] is True
    assert result["active_research_branch_display_parity_ok"] is True
    assert result["model"]["status"] == "HYP006_NO_MODEL_RELOAD_READ_ONLY"
    assert result["model"]["file_name"] != "legacy-model.ubj"
    assert result["audit"]["approved_for_paper_candidate"] is False
    assert result["audit"]["approved_for_live_real"] is False
    assert result["audit"]["post_requests_allowed"] is False
    assert result["scheduler"]["r1_task"]["task_name"] == "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection"
    assert len(result["recent_observations"]) == 3
    assert {row["symbol"] for row in result["recent_observations"]} == {"XRPUSDT", "BTCUSDT", "ETHUSDT"}


def test_binding_falls_back_without_ready_hyp006_reports(tmp_path: Path) -> None:
    legacy = {"branch_id": "HYP-005-R1", "fresh_ledger_namespace": "HYP005_R1"}
    assert hyp006_binding_available(tmp_path) is False
    assert apply_hyp006_operator_cockpit_binding(legacy, tmp_path) == legacy


def test_binding_availability_requires_28f_and_28g(tmp_path: Path) -> None:
    _seed_hyp006_reports(tmp_path)
    assert hyp006_binding_available(tmp_path) is True
