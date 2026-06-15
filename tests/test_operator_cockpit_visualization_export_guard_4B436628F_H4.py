from __future__ import annotations

import json
from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_h4_snapshot_sanitizes_sources_and_adds_visual_proxy(tmp_path: Path) -> None:
    from tradebot.operator_cockpit_hyp006_binding import apply_hyp006_operator_cockpit_binding
    from tradebot.operator_cockpit_hyp006_visualization_export_guard_hotfix import visualization_parity_ok

    reports = tmp_path / "reports" / "hyp006_r1_canonical"
    _write(reports / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260615T010000Z.json", json.dumps({
        "ok": True,
        "branch_id": "HYP-006-R1",
        "decision": "HYP006_R1_SHADOW_SAMPLE_EXPANSION_ACCEPTANCE_TRACKING_READY",
        "approved_for_acceptance_tracking": True,
        "approved_for_acceptance_review_candidate": False,
        "baseline_summary": {"unique_observation_ids": 2, "matured_count": 2, "win_count": 1, "loss_count": 1, "mean_return_bps": 25.0, "median_return_bps": 25.0, "profit_factor": 2.0},
        "acceptance_tracking_metrics": {"sample_target": 30, "sample_progress_pct": 6.666667, "acceptance_requirements_met": False},
        "blockers": ["SHADOW_SAMPLE_COUNT_BELOW_TARGET"],
    }))
    _write(reports / "4B436628F_hyp006_r1_operator_cockpit_baseline_20260615T010000Z.json", json.dumps({
        "ok": True,
        "branch_id": "HYP-006-R1",
        "baseline_summary": {"unique_observation_ids": 2, "matured_count": 2, "win_count": 1, "loss_count": 1, "mean_return_bps": 25.0, "median_return_bps": 25.0, "profit_factor": 2.0},
        "acceptance_baseline_metrics": {"sample_target": 30, "sample_progress_pct": 6.666667, "acceptance_requirements_met": False},
    }))
    _write(reports / "4B436628E_hyp006_r1_scheduler_execution_health_verify_20260615T010000Z.json", json.dumps({"scheduler_task_health": {"last_task_result": 0, "state": "Ready"}}))
    _write(reports / "4B436628D_hyp006_r1_shadow_ledger_20260615T010000Z.jsonl", "\n".join([
        json.dumps({"branch_id": "HYP-006-R1", "no_order_measurement_only": True, "observation_id": "HYP-006-A", "symbol": "BTCUSDT", "timestamp_utc": "2026-06-01T00:00:00+00:00", "forward_return_bps_final": 100.0, "spread_slippage_proxy_bps": 2.0}),
        json.dumps({"branch_id": "HYP-006-R1", "no_order_measurement_only": True, "observation_id": "HYP-006-B", "symbol": "ETHUSDT", "timestamp_utc": "2026-06-02T00:00:00+00:00", "forward_return_bps_final": -50.0, "spread_slippage_proxy_bps": 3.0}),
    ]) + "\n")

    legacy_snapshot = {"sources": {"latest_25v_logger": "reports\\hyp005_r1_canonical\\legacy.json", "latest_merged_ledger": "reports\\hyp005_r1_canonical\\legacy.jsonl"}}
    bound = apply_hyp006_operator_cockpit_binding(legacy_snapshot, tmp_path)

    assert bound["contract_version"] == "4B.4.3.6.6.28F-H4"
    assert "latest_25v_logger" not in bound["sources"]
    assert "hyp005_r1_canonical" not in json.dumps(bound["sources"])
    assert bound["sources"]["legacy_hyp005_active_sources_suppressed"] is True
    assert [row["cumulative_samples"] for row in bound["visualizations"]["sample_timeline"]] == [1, 2]
    assert len(bound["visualizations"]["mae_mfe_scatter"]) == 2
    assert bound["risk_sizing_evidence_export_gate"]["available"] is False
    assert visualization_parity_ok(bound)


def test_dashboard_html_uses_h4_visual_labels_and_guarded_button() -> None:
    from tradebot.operator_cockpit_v2_read_only import DASHBOARD_HTML

    assert "28F-H4 · READ ONLY" in DASHBOARD_HTML
    assert "28F-H4 · HYP006 GUARDED EXPORTS" in DASHBOARD_HTML
    assert "Risk-Sizing Evidence Yok" in DASHBOARD_HTML
    assert "cumulative_samples" in DASHBOARD_HTML
    assert "final edge proxy scatter" in DASHBOARD_HTML


def test_h4_keeps_mutating_gates_closed() -> None:
    from tradebot.operator_cockpit_hyp006_visualization_export_guard_hotfix import (
        OPERATOR_COCKPIT_HYP006_VISUALIZATION_EXPORT_GUARD_HOTFIX_VERSION,
        RISK_SIZING_EXPORT_UNAVAILABLE_REASON,
    )
    from tradebot.operator_cockpit_v2_read_only import (
        OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION,
        OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION,
        OPERATOR_COCKPIT_V2_NO_TRADING_ACTION,
    )

    assert OPERATOR_COCKPIT_HYP006_VISUALIZATION_EXPORT_GUARD_HOTFIX_VERSION == "4B.4.3.6.6.28F-H4"
    assert RISK_SIZING_EXPORT_UNAVAILABLE_REASON == "RISK_SIZING_RUNTIME_EVENT_NOT_FOUND"
    assert OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_TRADING_ACTION is True
