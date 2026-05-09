from __future__ import annotations

import json
from pathlib import Path

from tradebot.research_hyp005_no_order_shadow_planning import (
    HYP005_SHADOW_PLANNING_CONTRACT_VERSION,
    Hyp005ShadowPlanningLimits,
    build_hyp005_no_order_shadow_planning_report,
    validate_hyp005_source_reports,
)
from tools.run_hyp005_no_order_shadow_planning_4B436625U import main as tool_main


def _25s_pass() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25S",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "decision": "HYP005_EXPLORATION_PASS",
        "selected_candidate": {
            "strategy_family": "long_liquidity_sweep_reversal",
            "decision": "PASS",
            "spec": {
                "name": "long_liquidity_sweep_reversal",
                "lookback_bars": 24,
                "hold_bars": 6,
                "min_sweep_bps": 18.0,
                "min_wick_pct": 42.0,
                "compression_window": 12,
                "compression_baseline_bars": 48,
                "max_compression_ratio": 1.05,
                "diagnostic_only": False,
            },
        },
        "approved_for_research_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
    }


def _25t_pass() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25T",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "decision": "HYP005_ROBUSTNESS_PASS",
        "selected_candidate": {
            "strategy_family": "long_liquidity_sweep_reversal",
            "decision": "PASS",
            "spec": {
                "name": "long_liquidity_sweep_reversal",
                "lookback_bars": 24,
                "hold_bars": 6,
                "min_sweep_bps": 18.0,
                "min_wick_pct": 42.0,
                "compression_window": 12,
                "compression_baseline_bars": 48,
                "max_compression_ratio": 1.05,
                "diagnostic_only": False,
            },
            "metrics": {
                "signal_count": 28,
                "mean_net_edge_bps": 140.089198,
                "penalized_mean_net_edge_bps": 122.089198,
                "median_net_edge_bps": 109.881101,
                "profit_factor": 4.197094,
                "win_rate_pct": 71.428571,
                "oos_mean_net_edge_bps": 104.924999,
                "walk_forward_positive_rate_pct": 75.0,
                "top_win_dependency_pct": 36.380414,
                "dominant_symbol_pct": 35.714286,
                "wick_dependency_pct": 0.0,
                "symbols_traded": 4,
                "recent_30d_signal_count": 7,
                "recent_30d_mean_edge_bps": 93.5,
                "recent_60d_mean_edge_bps": 117.2,
                "small_sample_penalty_bps": 18.0,
            },
        },
        "warnings": ["ROBUST_SMALL_SAMPLE_PENALTY_APPLIED"],
        "approved_for_research_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
    }


def test_validate_hyp005_25s_and_25t_pass_chain() -> None:
    ok, reasons, warnings = validate_hyp005_source_reports(_25s_pass(), _25t_pass())
    assert ok is True
    assert reasons == []
    assert "SHADOW_SMALL_SAMPLE_CAUTION_REQUIRED" in warnings


def test_25u_builds_no_order_shadow_plan_and_candidate_spec() -> None:
    report = build_hyp005_no_order_shadow_planning_report(
        exploration_report=_25s_pass(),
        robustness_report=_25t_pass(),
        limits=Hyp005ShadowPlanningLimits(shadow_min_samples=30),
    )
    assert HYP005_SHADOW_PLANNING_CONTRACT_VERSION == "4B.4.3.6.6.25U"
    assert report["decision"] == "HYP005_SHADOW_PLAN_READY"
    assert report["approved_for_shadow_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    spec = report["candidate_spec"]
    assert spec["strategy_family"] == "long_liquidity_sweep_reversal"
    assert spec["entry_signal_definition"]["execution_mode"] == "NO_ORDER_SHADOW_ONLY"
    assert spec["guardrails"]["orders_allowed"] is False
    assert spec["guardrails"]["paper_transition_requires_new_gate"] is True
    assert spec["guardrails"]["live_transition_requires_separate_gate"] is True
    metric_names = {m["name"] for m in spec["required_shadow_acceptance_metrics"]}
    assert "shadow_sample_count" in metric_names
    assert "shadow_profit_factor" in metric_names


def test_25u_blocks_when_robustness_missing_or_not_pass() -> None:
    bad_25t = _25t_pass()
    bad_25t["decision"] = "HYP005_ROBUSTNESS_BLOCK"
    report = build_hyp005_no_order_shadow_planning_report(exploration_report=_25s_pass(), robustness_report=bad_25t)
    assert report["decision"] == "HYP005_SHADOW_PLAN_BLOCK"
    assert "HYP005_ROBUSTNESS_NOT_PASS" in report["reason_codes"]
    assert report["approved_for_shadow_candidate"] is False
    assert report["candidate_spec"] is None


def test_25u_blocks_source_guardrail_violation() -> None:
    bad_25t = _25t_pass()
    bad_25t["approved_for_paper_candidate"] = True
    report = build_hyp005_no_order_shadow_planning_report(exploration_report=_25s_pass(), robustness_report=bad_25t)
    assert report["decision"] == "HYP005_SHADOW_PLAN_BLOCK"
    assert "25T_PAPER_APPROVAL_GUARDRAIL_VIOLATION" in report["reason_codes"]
    assert report["approved_for_paper_candidate"] is False


def test_tool_writes_report_and_candidate_spec_json(tmp_path: Path) -> None:
    s_path = tmp_path / "25s.json"
    t_path = tmp_path / "25t.json"
    s_path.write_text(json.dumps(_25s_pass()), encoding="utf-8")
    t_path.write_text(json.dumps(_25t_pass()), encoding="utf-8")
    out = tmp_path / "reports"
    rc = tool_main([
        "--input-json",
        str(s_path),
        "--input-json",
        str(t_path),
        "--out-dir",
        str(out),
        "--review-ok",
    ])
    assert rc == 0
    reports = list(out.glob("4B436625U_hyp005_no_order_shadow_planning_*.json"))
    specs = list(out.glob("4B436625U_hyp005_no_order_shadow_candidate_spec_*.json"))
    assert len(reports) == 1
    assert len(specs) == 1
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    spec = json.loads(specs[0].read_text(encoding="utf-8"))
    assert report["decision"] == "HYP005_SHADOW_PLAN_READY"
    assert report["candidate_spec_json"] == str(specs[0])
    assert spec["guardrails"]["orders_allowed"] is False
    assert spec["status"] == "NO_ORDER_SHADOW_PLAN_READY"
