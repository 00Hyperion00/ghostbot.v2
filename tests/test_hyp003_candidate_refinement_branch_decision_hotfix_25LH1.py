from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.run_hyp003_candidate_refinement_branch_decision_4B436625L import (
    HYP003_REFINEMENT_CLI_HOTFIX_VERSION,
    _candidate_key_text,
)


def _selected_candidate() -> dict:
    return {
        "symbol": "ETHUSDT",
        "interval": "4h",
        "strategy_family": "range_mean_reversion",
        "regime": "range",
        "decision": "PASS",
        "score": 120.0,
        "spec": {"name": "range_mean_reversion", "regime": "range"},
        "metrics": {
            "signal_count": 67,
            "mean_net_edge_bps": 23.97,
            "median_net_edge_bps": 31.59,
            "profit_factor": 1.58,
            "oos_mean_net_edge_bps": 12.0,
            "walk_forward_positive_rate_pct": 75.0,
        },
        "reason_codes": [],
    }


def _report_25j_no_alternate() -> dict:
    selected = _selected_candidate()
    return {
        "contract_version": "4B.4.3.6.6.25J",
        "phase": "25J",
        "report_type": "hyp003_regime_specific_strategy_family_exploration_gate",
        "decision": "HYP003_EXPLORATION_PASS",
        "hypothesis_id": "HYP-003",
        "selected_candidate": selected,
        "candidates": [selected],
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
        "candidate_spec": {
            "hypothesis_id": "HYP-003",
            "symbol": "ETHUSDT",
            "interval": "4h",
            "strategy": "range_mean_reversion",
            "regime": "range",
        },
        "signal_metrics": {
            "signal_count": 66,
            "mean_net_edge_bps": -11.606522,
            "median_net_edge_bps": -24.400868,
            "profit_factor": 0.74203,
        },
        "walk_forward_positive_rate_pct": 25.0,
        "oos_segment": {"name": "oos_last_30pct", "mean_net_edge_bps": -21.839317},
        "reason_codes": [
            "ROBUST_MEAN_EDGE_LOW",
            "ROBUST_MEDIAN_EDGE_LOW",
            "ROBUST_OOS_EDGE_LOW",
            "ROBUST_PROFIT_FACTOR_LOW",
            "ROBUST_WALK_FORWARD_STABILITY_LOW",
            "ROBUST_WIN_RATE_LOW",
        ],
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def test_25lh1_declares_cli_hotfix_version() -> None:
    assert HYP003_REFINEMENT_CLI_HOTFIX_VERSION == "4B.4.3.6.6.25L-H1"


def test_25lh1_candidate_key_text_handles_none_and_valid_candidate() -> None:
    assert _candidate_key_text(None) == "NONE"
    assert _candidate_key_text({"key": None}) == "NONE"
    assert _candidate_key_text({"key": {"symbol": "ETHUSDT", "interval": "4h", "strategy_family": "range_mean_reversion", "regime": "range"}}) == "ETHUSDT 4h range_mean_reversion range"


def test_25lh1_cli_closure_path_no_selected_candidate_does_not_crash(tmp_path: Path) -> None:
    input_25j = tmp_path / "25j.json"
    input_25k = tmp_path / "25k.json"
    out_dir = tmp_path / "reports"
    input_25j.write_text(json.dumps(_report_25j_no_alternate()), encoding="utf-8")
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
    assert "HYP003_BRANCH_CLOSURE_RECOMMENDED" in result.stdout
    assert "selected_next_candidate: NONE" in result.stdout
    assert list(out_dir.glob("4B436625L_hyp003_candidate_refinement_branch_decision_*.json"))
    assert not list(out_dir.glob("4B436625L_hyp003_next_candidate_for_25K_*.json"))
