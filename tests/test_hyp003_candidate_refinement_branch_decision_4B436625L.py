from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp003_candidate_refinement_branch_decision import (
    build_hyp003_candidate_refinement_branch_decision,
    extract_hyp003_evidence,
)


def _candidate(symbol: str, family: str, regime: str, score: float, signal_count: int, mean: float, median: float, pf: float, oos: float, decision: str = "PASS") -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25J",
        "symbol": symbol,
        "interval": "4h",
        "strategy_family": family,
        "regime": regime,
        "decision": decision,
        "ok": decision == "PASS",
        "score": score,
        "reason_codes": [] if decision == "PASS" else ["HYP003_MEAN_EDGE_LOW"],
        "warnings": [],
        "spec": {"name": family, "regime": regime, "hold_bars": 1, "cost_bps": 16.0},
        "metrics": {
            "signal_count": signal_count,
            "mean_net_edge_bps": mean,
            "median_net_edge_bps": median,
            "profit_factor": pf,
            "oos_mean_net_edge_bps": oos,
            "walk_forward_positive_rate_pct": 75.0,
        },
    }


def _report_25j(with_alternate: bool = True) -> dict:
    selected = _candidate("ETHUSDT", "range_mean_reversion", "range", 120.0, 67, 23.97, 31.59, 1.58, 12.0)
    candidates = [selected]
    if with_alternate:
        candidates.append(_candidate("BTCUSDT", "trend_pullback_continuation", "trend", 105.0, 52, 11.5, 7.2, 1.31, 3.5))
    candidates.append(_candidate("SOLUSDT", "low_vol_breakout_probe", "low_vol", -50.0, 10, -2.0, -3.0, 0.7, -5.0, decision="BLOCK"))
    return {
        "contract_version": "4B.4.3.6.6.25J",
        "phase": "25J",
        "report_type": "hyp003_regime_specific_strategy_family_exploration_gate",
        "decision": "HYP003_EXPLORATION_PASS",
        "hypothesis_id": "HYP-003",
        "selected_candidate": selected,
        "candidates": candidates,
        "approved_for_research_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def _report_25k_block() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25K",
        "phase": "4B.4.3.6.6.25K",
        "report_type": "hyp003_robustness_walkforward_confirmation_gate",
        "decision": "HYP003_ROBUSTNESS_BLOCK",
        "candidate_spec": {"hypothesis_id": "HYP-003", "symbol": "ETHUSDT", "interval": "4h", "strategy": "range_mean_reversion", "regime": "range"},
        "signal_metrics": {"signal_count": 66, "mean_net_edge_bps": -11.606522, "median_net_edge_bps": -24.400868, "profit_factor": 0.74203},
        "walk_forward_positive_rate_pct": 25.0,
        "oos_segment": {"name": "oos_last_30pct", "mean_net_edge_bps": -21.839317},
        "reason_codes": ["ROBUST_MEAN_EDGE_LOW", "ROBUST_MEDIAN_EDGE_LOW", "ROBUST_OOS_EDGE_LOW", "ROBUST_PROFIT_FACTOR_LOW", "ROBUST_WALK_FORWARD_STABILITY_LOW", "ROBUST_WIN_RATE_LOW"],
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def _report_25k_pass() -> dict:
    payload = _report_25k_block()
    payload["decision"] = "HYP003_ROBUSTNESS_PASS"
    payload["signal_metrics"] = {"signal_count": 70, "mean_net_edge_bps": 9.0, "median_net_edge_bps": 5.0, "profit_factor": 1.25}
    payload["walk_forward_positive_rate_pct"] = 75.0
    payload["oos_segment"] = {"name": "oos_last_30pct", "mean_net_edge_bps": 4.0}
    payload["reason_codes"] = []
    payload["approved_for_research_candidate"] = True
    return payload


def test_25l_selects_next_25j_pass_candidate_after_25k_block() -> None:
    report = build_hyp003_candidate_refinement_branch_decision([("25j.json", _report_25j()), ("25k.json", _report_25k_block())])
    assert report["decision"] == "HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS"
    assert report["selected_failed_terminal"] is True
    assert report["selected_next_candidate"]["key"]["symbol"] == "BTCUSDT"
    assert report["next_candidate_25k_report"]["selected_candidate"]["symbol"] == "BTCUSDT"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False


def test_25l_recommends_branch_closure_when_no_alternate_candidate() -> None:
    report = build_hyp003_candidate_refinement_branch_decision([("25j.json", _report_25j(with_alternate=False)), ("25k.json", _report_25k_block())])
    assert report["decision"] == "HYP003_BRANCH_CLOSURE_RECOMMENDED"
    assert "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE" in report["reason_codes"]
    assert report["approved_for_research_candidate"] is False
    assert report["approved_for_live_real"] is False


def test_25l_continues_if_25k_passed() -> None:
    report = build_hyp003_candidate_refinement_branch_decision([("25j.json", _report_25j()), ("25k.json", _report_25k_pass())])
    assert report["decision"] == "HYP003_BRANCH_RESEARCH_CONTINUE"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_paper_candidate"] is False


def test_extract_hyp003_evidence_separates_25j_and_25k() -> None:
    exploration, robustness = extract_hyp003_evidence([("25j.json", _report_25j()), ("25k.json", _report_25k_block())])
    assert len(exploration) >= 2
    assert len(robustness) == 1
    assert robustness[0].key.strategy_family == "range_mean_reversion"


def test_tool_writes_report_and_next_candidate_json(tmp_path: Path) -> None:
    input_25j = tmp_path / "25j.json"
    input_25k = tmp_path / "25k.json"
    out_dir = tmp_path / "reports"
    input_25j.write_text(json.dumps(_report_25j()), encoding="utf-8")
    input_25k.write_text(json.dumps(_report_25k_block()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp003_candidate_refinement_branch_decision_4B436625L.py",
            "--input-json",
            str(input_25j),
            "--input-json",
            str(input_25k),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS" in result.stdout
    assert list(out_dir.glob("4B436625L_hyp003_candidate_refinement_branch_decision_*.json"))
    assert list(out_dir.glob("4B436625L_hyp003_next_candidate_for_25K_*.json"))
