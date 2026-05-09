from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tradebot.research_hyp003_robustness_walkforward import (
    Hyp003CandidateSpec,
    Hyp003RobustnessLimits,
    build_hyp003_robustness_walkforward_report,
    parse_hyp003_candidate_from_25j,
)


def _candidate_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25J",
        "decision": "HYP003_EXPLORATION_PASS",
        "hypothesis_id": "HYP-003",
        "selected": "ETHUSDT 4h range_mean_reversion range",
        "selected_signal_count": 67,
        "selected_mean_net_edge_bps": 23.979025,
        "selected_median_net_edge_bps": 31.590359,
        "selected_profit_factor": 1.581891,
    }


def _range_reversion_market(rows: int = 720, adverse_tail: bool = False) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="4h", tz="UTC")
    close: list[float] = []
    price = 100.0
    # Repeated excursions from mean to bands and snap back.
    pattern = [0.0, -0.4, -0.9, -1.5, -2.3, -3.2, -1.1, -0.2, 0.3, 0.8, 1.5, 2.4, 3.2, 1.1, 0.2, -0.2]
    for idx in range(rows):
        value = 100.0 + pattern[idx % len(pattern)]
        if adverse_tail and idx > rows * 0.72:
            # Break mean reversion in OOS: extremes continue instead of reverting.
            value = 100.0 + (idx - int(rows * 0.72)) * 0.035 + pattern[idx % len(pattern)] * 1.2
        close.append(value)
    close_arr = np.asarray(close, dtype="float64")
    return pd.DataFrame(
        {
            "timestamp": timestamps.astype("int64") // 1_000_000,
            "open": np.r_[close_arr[0], close_arr[:-1]],
            "high": close_arr + 0.35,
            "low": close_arr - 0.35,
            "close": close_arr,
            "volume": 1000 + np.arange(rows) % 20,
        }
    )


def test_parse_selected_candidate_from_25j_report() -> None:
    spec = parse_hyp003_candidate_from_25j(_candidate_report())
    assert spec.hypothesis_id == "HYP-003"
    assert spec.symbol == "ETHUSDT"
    assert spec.interval == "4h"
    assert spec.strategy == "range_mean_reversion"
    assert spec.regime == "range"


def test_robustness_gate_passes_balanced_positive_candidate() -> None:
    report = build_hyp003_robustness_walkforward_report(
        _range_reversion_market(),
        Hyp003CandidateSpec(hold_bars=2),
        Hyp003RobustnessLimits(min_signal_count=20, min_recent_window_signal_count=3, max_top_win_dependency_pct=70.0, min_win_rate_pct=45.0),
    )
    assert report["decision"] == "HYP003_ROBUSTNESS_PASS", report["reason_codes"]
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["signal_metrics"]["median_net_edge_bps"] > 0
    assert report["walk_forward_positive_rate_pct"] >= 60


def test_robustness_gate_blocks_negative_oos_candidate() -> None:
    report = build_hyp003_robustness_walkforward_report(
        _range_reversion_market(adverse_tail=True),
        Hyp003CandidateSpec(hold_bars=1),
        Hyp003RobustnessLimits(min_signal_count=20, min_recent_window_signal_count=3, max_top_win_dependency_pct=90.0, min_win_rate_pct=45.0),
    )
    assert report["decision"] == "HYP003_ROBUSTNESS_BLOCK"
    assert report["approved_for_live_real"] is False
    assert report["reason_codes"]


def test_robustness_report_preserves_guardrails() -> None:
    report = build_hyp003_robustness_walkforward_report(
        _range_reversion_market(),
        Hyp003CandidateSpec(hold_bars=2),
        Hyp003RobustnessLimits(min_signal_count=20, min_recent_window_signal_count=3, max_top_win_dependency_pct=70.0, min_win_rate_pct=45.0),
    )
    assert report["guardrails"]["post_requests_allowed"] is False
    assert report["guardrails"]["training_allowed"] is False
    assert report["reload_performed"] is False
    assert report["order_actions_performed"] is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    input_json = tmp_path / "25j.json"
    input_csv = tmp_path / "market.csv"
    out_dir = tmp_path / "reports"
    input_json.write_text(json.dumps(_candidate_report()), encoding="utf-8")
    _range_reversion_market().to_csv(input_csv, index=False)
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp003_robustness_walkforward_4B436625K.py",
            "--input-json",
            str(input_json),
            "--input-csv",
            str(input_csv),
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
    reports = list(out_dir.glob("4B436625K_hyp003_robustness_walkforward_confirmation_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["approved_for_training_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
