from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tradebot.futures_funding_open_interest_edge_exploration import (
    FuturesEdgeLimits,
    FuturesEdgeSpec,
    build_futures_funding_open_interest_edge_exploration,
    evaluate_futures_strategy_edge,
)


def _positive_funding_reversal_frame(rows: int = 420) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 1000 + np.cumsum(rng.normal(0, 0.3, rows))
    funding = np.zeros(rows)
    long_short = np.ones(rows)
    taker_ratio = np.ones(rows)
    # Create repeated negative funding/crowding points followed by positive forward movement.
    for idx in range(80, rows - 8, 30):
        funding[idx - 4 : idx + 1] = -0.0015
        long_short[idx - 4 : idx + 1] = 0.72
        taker_ratio[idx - 4 : idx + 1] = 0.85
        close[idx + 3 : idx + 8] += 8.0
    # Create repeated positive funding/crowding points followed by negative forward movement.
    for idx in range(95, rows - 8, 30):
        funding[idx - 4 : idx + 1] = 0.0015
        long_short[idx - 4 : idx + 1] = 1.35
        taker_ratio[idx - 4 : idx + 1] = 1.20
        close[idx + 3 : idx + 8] -= 8.0
    high = close + 2.0
    low = close - 2.0
    volume = np.full(rows, 1000.0)
    return pd.DataFrame(
        {
            "open_time": np.arange(rows) * 60_000,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "funding_rate": funding,
            "sum_open_interest": 1_000_000 + np.arange(rows) * 50,
            "long_short_ratio": long_short,
            "taker_buy_sell_ratio": taker_ratio,
        }
    )


def _negative_frame(rows: int = 420) -> pd.DataFrame:
    frame = _positive_funding_reversal_frame(rows)
    # Reverse the future response so contrarian funding signals lose after costs.
    frame["close"] = frame["close"].iloc[::-1].to_numpy()
    frame["high"] = frame["close"] + 2.0
    frame["low"] = frame["close"] - 2.0
    return frame


def test_futures_edge_exploration_passes_positive_funding_candidate() -> None:
    frame = _positive_funding_reversal_frame()
    spec = FuturesEdgeSpec(name="funding_crowding_reversal", family="funding_contrarian", cost_bps=2.0, forward_bars=4)
    limits = FuturesEdgeLimits(
        min_signal_count=8,
        min_clean_samples=100,
        min_profit_factor=1.05,
        min_win_rate_pct=45.0,
        max_drawdown_pct=50.0,
        min_metric_coverage_pct=5.0,
        min_oos_mean_net_edge_bps=-20.0,
        min_walk_forward_positive_rate_pct=25.0,
    )
    result = evaluate_futures_strategy_edge(frame, spec, symbol="ETHUSDT", interval="1h", limits=limits)
    assert result.decision == "PASS"
    assert result.ok is True
    assert result.mean_net_edge_bps > 0
    assert result.approvable is True


def test_futures_edge_exploration_blocks_negative_candidate() -> None:
    frame = _negative_frame()
    spec = FuturesEdgeSpec(name="funding_crowding_reversal", family="funding_contrarian", cost_bps=15.0, forward_bars=4)
    limits = FuturesEdgeLimits(min_signal_count=8, min_clean_samples=100, min_metric_coverage_pct=5.0)
    result = evaluate_futures_strategy_edge(frame, spec, symbol="ETHUSDT", interval="1h", limits=limits)
    assert result.decision == "BLOCK"
    assert any(code in result.reason_codes for code in ["EDGE_EXPECTED_EDGE_LOW", "EDGE_MEDIAN_EDGE_LOW", "EDGE_PROFIT_FACTOR_LOW", "EDGE_WIN_RATE_LOW"])
    assert result.ok is False


def test_build_report_blocks_paper_and_live_even_when_research_passes() -> None:
    frame = _positive_funding_reversal_frame()
    limits = FuturesEdgeLimits(
        min_signal_count=8,
        min_clean_samples=100,
        min_profit_factor=1.05,
        min_win_rate_pct=45.0,
        max_drawdown_pct=50.0,
        min_metric_coverage_pct=5.0,
        min_oos_mean_net_edge_bps=-20.0,
        min_walk_forward_positive_rate_pct=25.0,
    )
    specs = [FuturesEdgeSpec(name="funding_crowding_reversal", family="funding_contrarian", cost_bps=2.0, forward_bars=4)]
    report = build_futures_funding_open_interest_edge_exploration({("ETHUSDT", "1h"): frame}, source="unit", limits=limits, specs=specs)
    assert report["decision"] == "PASS"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["guardrails"]["post_requests_allowed"] is False


def test_diagnostic_strategy_is_not_approvable() -> None:
    frame = _positive_funding_reversal_frame()
    spec = FuturesEdgeSpec(name="diagnostic_taker_flow_tick", family="diagnostic", approvable=False, cost_bps=0.0)
    result = evaluate_futures_strategy_edge(frame, spec, symbol="ETHUSDT", interval="1h", limits=FuturesEdgeLimits(min_metric_coverage_pct=0.0))
    assert result.decision == "BLOCK"
    assert "DIAGNOSTIC_STRATEGY_NOT_APPROVABLE" in result.reason_codes


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    frame = _positive_funding_reversal_frame()
    csv_path = tmp_path / "ETHUSDT_1h_futures.csv"
    frame.to_csv(csv_path, index=False)
    out_dir = tmp_path / "reports"
    script = Path(__file__).resolve().parents[1] / "tools" / "run_futures_funding_open_interest_edge_exploration_4B436625B.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-csv",
            str(csv_path),
            "--symbols",
            "ETHUSDT",
            "--intervals",
            "1h",
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "futures funding/open-interest edge exploration" in completed.stdout
    reports = list(out_dir.glob("4B436625B_futures_funding_open_interest_edge_exploration_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
