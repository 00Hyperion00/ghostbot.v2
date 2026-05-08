from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tradebot.timeframe_symbol_strategy_edge_exploration import (
    EdgeExplorationLimits,
    StrategyEdgeSpec,
    build_timeframe_symbol_strategy_edge_exploration,
    evaluate_strategy_edge,
)


def _trend_frame(rows: int = 240, *, direction: float = 1.0) -> pd.DataFrame:
    base = 100.0 + direction * np.arange(rows) * 0.08
    # Add a small oscillation so indicators are non-degenerate.
    close = base + np.sin(np.arange(rows) / 6.0) * 0.03
    open_ = close - direction * 0.02
    high = np.maximum(open_, close) + 0.05
    low = np.minimum(open_, close) - 0.05
    volume = np.full(rows, 100.0)
    return pd.DataFrame(
        {
            "open_time": np.arange(rows) * 60_000,
            "close_time": (np.arange(rows) + 1) * 60_000,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": volume * close,
        }
    )


def _chop_frame(rows: int = 240) -> pd.DataFrame:
    close = 100.0 + np.sin(np.arange(rows) / 2.0) * 0.12
    open_ = close + np.cos(np.arange(rows) / 3.0) * 0.03
    high = np.maximum(open_, close) + 0.04
    low = np.minimum(open_, close) - 0.04
    volume = np.full(rows, 100.0)
    return pd.DataFrame(
        {
            "open_time": np.arange(rows) * 60_000,
            "close_time": (np.arange(rows) + 1) * 60_000,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": volume * close,
        }
    )


def _loose_limits() -> EdgeExplorationLimits:
    return EdgeExplorationLimits(
        min_clean_samples=80,
        min_signal_count=10,
        min_signal_coverage_pct=1.0,
        max_signal_coverage_pct=99.0,
        max_dominant_action_pct=100.0,
        min_mean_net_edge_bps=0.1,
        min_median_net_edge_bps=-2.0,
        min_win_rate_pct=45.0,
        min_profit_factor=1.0,
    )


def test_edge_exploration_passes_positive_trend_candidate() -> None:
    report = build_timeframe_symbol_strategy_edge_exploration(
        {("ETHUSDT", "1m"): _trend_frame()},
        strategy_specs=[StrategyEdgeSpec("trend_following_ema")],
        cost_bps=0.5,
        limits=_loose_limits(),
    )
    assert report["decision"] == "PASS"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["selected_strategy"] == "trend_following_ema"


def test_edge_exploration_blocks_negative_edge_candidate() -> None:
    candidate = evaluate_strategy_edge(
        _chop_frame(),
        symbol="ETHUSDT",
        interval="1m",
        spec=StrategyEdgeSpec("diagnostic_every_trend_tick", approvable=False),
        cost_bps=30.0,
        limits=_loose_limits(),
    )
    assert candidate["decision"] == "BLOCK"
    assert "DIAGNOSTIC_STRATEGY_NOT_APPROVABLE" in candidate["reason_codes"]
    assert candidate["approved_for_live_real"] is False


def test_selection_prefers_best_symbol_timeframe() -> None:
    report = build_timeframe_symbol_strategy_edge_exploration(
        {
            ("CHOPUSDT", "1m"): _chop_frame(),
            ("TRENDUSDT", "5m"): _trend_frame(),
        },
        strategy_specs=[StrategyEdgeSpec("trend_following_ema")],
        cost_bps=0.5,
        limits=_loose_limits(),
    )
    assert report["selected_symbol"] == "TRENDUSDT"
    assert report["selected_interval"] == "5m"


def test_report_blocks_when_no_strategy_has_edge() -> None:
    report = build_timeframe_symbol_strategy_edge_exploration(
        {("ETHUSDT", "1m"): _chop_frame()},
        strategy_specs=[StrategyEdgeSpec("rsi_bollinger_reversion")],
        cost_bps=50.0,
        limits=_loose_limits(),
    )
    assert report["decision"] == "BLOCK"
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "trend.csv"
    out_dir = tmp_path / "reports"
    _trend_frame().to_csv(csv_path, index=False)
    cmd = [
        sys.executable,
        "tools/run_timeframe_symbol_strategy_edge_exploration_4B436624M.py",
        "--input-csv",
        str(csv_path),
        "--symbols",
        "TESTUSDT",
        "--intervals",
        "1m",
        "--cost-bps",
        "0.5",
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode in (0, 2), result.stderr + result.stdout
    reports = sorted(out_dir.glob("4B436624M_timeframe_symbol_strategy_edge_exploration_*.json"))
    assert reports
    payload = json.loads(reports[-1].read_text(encoding="utf-8"))
    assert payload["contract_version"] == "4B.4.3.6.6.24M"
    assert payload["guardrails"]["post_requests_allowed"] is False
