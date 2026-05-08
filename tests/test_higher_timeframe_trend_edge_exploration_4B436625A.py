from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tradebot.higher_timeframe_trend_edge_exploration import (
    HigherTimeframeStrategySpec,
    HigherTimeframeTrendLimits,
    build_timeframe_symbol_strategy_edge_exploration,
    evaluate_strategy_edge,
)


def _trend_df(rows: int = 700) -> pd.DataFrame:
    idx = np.arange(rows, dtype=float)
    close = 100.0 + idx * 0.18 + 1.25 * np.sin(idx / 9.0)
    open_ = close - 0.08
    high = close + 0.35
    low = close - 0.35
    volume = 1000.0 + 100.0 * np.sin(idx / 17.0)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def _mean_reverting_negative_df(rows: int = 700) -> pd.DataFrame:
    idx = np.arange(rows, dtype=float)
    close = 100.0 + 1.5 * np.sin(idx / 2.0)
    open_ = close + 0.05 * np.cos(idx)
    high = close + 0.30
    low = close - 0.30
    volume = 1000.0 + 20.0 * np.cos(idx / 5.0)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def test_edge_exploration_passes_positive_higher_timeframe_trend_candidate() -> None:
    report = build_timeframe_symbol_strategy_edge_exploration(
        {("TESTUSDT", "1h"): _trend_df()},
        source="synthetic:trend",
        cost_bps=1.0,
        strategy_specs=(HigherTimeframeStrategySpec("ema_trend_continuation", "trend_following"),),
        limits=HigherTimeframeTrendLimits(min_signal_count=30, max_signal_coverage_pct=95.0, max_dominant_action_pct=100.0, max_drawdown_pct=100.0),
    )

    assert report["decision"] == "RESEARCH_CANDIDATE"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["selected"]["mean_net_edge_bps"] > 3.0


def test_edge_exploration_blocks_negative_edge_candidate() -> None:
    report = build_timeframe_symbol_strategy_edge_exploration(
        {("TESTUSDT", "1h"): _mean_reverting_negative_df()},
        source="synthetic:negative",
        cost_bps=25.0,
        strategy_specs=(HigherTimeframeStrategySpec("ema_trend_continuation", "trend_following"),),
    )

    assert report["decision"] == "BLOCK"
    assert report["approved_for_research_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert "NO_HIGHER_TIMEFRAME_TREND_EDGE_CANDIDATE_PASSED" in report["reason_codes"]


def test_diagnostic_strategy_cannot_be_approved() -> None:
    result = evaluate_strategy_edge(
        _trend_df(),
        symbol="TESTUSDT",
        interval="1h",
        spec=HigherTimeframeStrategySpec("diagnostic_every_trend_tick", "diagnostic", approvable=False),
        cost_bps=1.0,
        limits=HigherTimeframeTrendLimits(min_signal_count=30, max_signal_coverage_pct=99.0, max_dominant_action_pct=100.0, max_drawdown_pct=100.0),
    )

    assert result.decision == "BLOCK"
    assert "DIAGNOSTIC_STRATEGY_NOT_APPROVABLE" in result.reason_codes


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "TESTUSDT_1h.csv"
    _trend_df().to_csv(csv_path, index=False)
    out_dir = tmp_path / "reports"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "tools/run_higher_timeframe_trend_edge_exploration_4B436625A.py",
            "--input-csv",
            str(csv_path),
            "--symbols",
            "TESTUSDT",
            "--intervals",
            "1h",
            "--out-dir",
            str(out_dir),
            "--cost-bps",
            "1",
            "--review-ok",
        ],
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode in (0, 2), completed.stderr + completed.stdout
    reports = list(out_dir.glob("4B436625A_higher_timeframe_trend_edge_exploration_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["approved_for_training_candidate"] is False
    assert payload["approved_for_live_real"] is False


def test_report_keeps_guardrails_closed() -> None:
    report = build_timeframe_symbol_strategy_edge_exploration(
        {("TESTUSDT", "1h"): _trend_df()},
        source="synthetic:guardrail",
        cost_bps=1.0,
        strategy_specs=(HigherTimeframeStrategySpec("ema_trend_continuation", "trend_following"),),
        limits=HigherTimeframeTrendLimits(min_signal_count=30, max_signal_coverage_pct=95.0, max_dominant_action_pct=100.0, max_drawdown_pct=100.0),
    )
    assert report["guardrails"]["backtest_pass_is_not_paper_permission"] is True
    assert report["guardrails"]["paper_pass_is_not_live_permission"] is True
    assert report["post_requests_allowed"] is False
