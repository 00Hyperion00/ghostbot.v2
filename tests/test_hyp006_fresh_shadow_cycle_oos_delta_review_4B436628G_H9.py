from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_fresh_shadow_cycle_oos_delta_review import (
    BLOCKED_DECISION,
    READY_DECISION,
    build_fresh_shadow_cycle_oos_delta_review,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _h3(stamp: str, *, candidate: int, near: int, bnb_near: int) -> tuple[str, dict]:
    return (
        f"4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss_{stamp}.json",
        {
            "contract_version": "4B.4.3.6.6.28G-H3",
            "branch_id": "HYP-006-R1",
            "branch_name": "failed_downside_sweep_reversal_continuation_short",
            "timeframe": "4h",
            "read_only": True,
            "candidate_count": candidate,
            "near_miss_count": near,
            "trigger_count": 0,
            "scanned_candle_count": 1000,
            "symbol_near_miss_counter": {"BNBUSDT": bnb_near},
            "symbol_candidate_counter": {"BNBUSDT": bnb_near + 2},
        },
    )


def _h8(stamp: str, *, matured: int, matured_delta: int, worst_return: float = -312.0, worst_mae: float = -426.0) -> tuple[str, dict]:
    return (
        f"4B436628G_H8_hyp006_r1_bnbusdt_overlay_oos_evaluation_runtime_activation_blocked_decision_{stamp}.json",
        {
            "contract_version": "4B.4.3.6.6.28G-H8",
            "decision": "HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_READY_RUNTIME_ACTIVATION_BLOCKED",
            "ok": True,
            "read_only": True,
            "approved_for_bnbusdt_oos_evaluation": True,
            "approved_for_oos_monitoring_continuation": True,
            "approved_for_runtime_overlay_activation_candidate": False,
            "approved_for_parameter_relaxation_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
            "order_actions_performed": False,
            "oos_guard_pass": True,
            "oos_guard_reasons": [],
            "latest_bnbusdt_measurement_summary": {
                "symbol": "BNBUSDT",
                "event_count": matured,
                "matured_count": matured,
                "win_rate_pct": 76.9,
                "mean_return_bps": 126.6,
                "median_return_bps": 142.9,
                "profit_factor": 5.4,
                "worst_return_bps": worst_return,
                "worst_mae_bps": worst_mae,
                "net_return_bps": 1645.0,
            },
            "oos_delta_summary": {
                "event_count_delta": matured_delta,
                "matured_count_delta": matured_delta,
                "win_rate_pct_delta": 1.9,
                "mean_return_bps_delta": 25.0,
                "profit_factor_delta": 1.1,
                "worst_return_bps_delta": 0.0,
                "worst_mae_bps_delta": 0.0,
            },
            "tail_risk_assessment": {
                "tail_risk_monitoring_required": True,
                "tail_risk_reasons": ["WORST_MAE_MONITORING_REQUIRED"],
                "latest_worst_return_bps": worst_return,
                "latest_worst_mae_bps": worst_mae,
            },
        },
    )


def _write_minimal_h4_to_h7(base: Path) -> None:
    artifacts = [
        ("4B436628G_H4_hyp006_r1_near_miss_outcome_attribution_20260619T220001Z.json", "4B.4.3.6.6.28G-H4", "HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_READY"),
        ("4B436628G_H5_hyp006_r1_counterfactual_filter_candidate_ranking_20260619T220002Z.json", "4B.4.3.6.6.28G-H5", "HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_READY"),
        ("4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design_20260619T220003Z.json", "4B.4.3.6.6.28G-H6", "HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_READY"),
        ("4B436628G_H7_hyp006_r1_no_order_overlay_simulation_bnbusdt_primary_filter_shadow_measurement_20260619T220004Z.json", "4B.4.3.6.6.28G-H7", "NO_ORDER_BNBUSDT_PRIMARY_OVERLAY_SHADOW_MEASUREMENT_READY"),
    ]
    for name, contract, decision in artifacts:
        _write(base / name, {"contract_version": contract, "decision": decision, "read_only": True})


def test_ready_report_keeps_paper_transition_blocked(tmp_path: Path) -> None:
    previous_name, previous_payload = _h3("20260618T210504Z", candidate=30, near=20, bnb_near=12)
    latest_name, latest_payload = _h3("20260619T210504Z", candidate=35, near=25, bnb_near=14)
    _write(tmp_path / previous_name, previous_payload)
    _write(tmp_path / latest_name, latest_payload)
    _write_minimal_h4_to_h7(tmp_path)
    h8_name, h8_payload = _h8("20260619T220005Z", matured=14, matured_delta=1)
    _write(tmp_path / h8_name, h8_payload)

    report = build_fresh_shadow_cycle_oos_delta_review(tmp_path)

    assert report["decision"] == READY_DECISION
    assert report["h4_h8_evidence_complete"] is True
    assert report["approved_for_hyp006_oos_monitoring_continuation"] is True
    assert report["approved_for_paper_transition_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["trading_action_performed"] is False
    assert report["bnbusdt_matured_count"] == 14
    assert report["bnbusdt_matured_count_delta"] == 1
    assert report["h3_delta_summary"]["bnbusdt_near_miss_count_delta"] == 2


def test_missing_h4_to_h8_blocks_review(tmp_path: Path) -> None:
    latest_name, latest_payload = _h3("20260619T210504Z", candidate=35, near=25, bnb_near=14)
    _write(tmp_path / latest_name, latest_payload)

    report = build_fresh_shadow_cycle_oos_delta_review(tmp_path)

    assert report["decision"] == BLOCKED_DECISION
    assert report["approved_for_hyp006_oos_delta_review"] is False
    assert any(str(item).startswith("FRESH_H4_H8_EVIDENCE_MISSING") for item in report["blockers"])
    assert report["approved_for_paper_transition_candidate"] is False


def test_tail_risk_deterioration_blocks_promotion(tmp_path: Path) -> None:
    latest_name, latest_payload = _h3("20260619T210504Z", candidate=35, near=25, bnb_near=14)
    _write(tmp_path / latest_name, latest_payload)
    _write_minimal_h4_to_h7(tmp_path)
    h8_name, h8_payload = _h8("20260619T220005Z", matured=14, matured_delta=1)
    h8_payload["tail_risk_assessment"]["tail_risk_reasons"] = ["WORST_RETURN_DETERIORATED"]
    _write(tmp_path / h8_name, h8_payload)

    report = build_fresh_shadow_cycle_oos_delta_review(tmp_path)

    assert report["tail_risk_worsened"] is True
    assert report["decision"] == BLOCKED_DECISION
    assert "TAIL_RISK_DETERIORATED" in report["blockers"]
    assert report["approved_for_live_real"] is False
