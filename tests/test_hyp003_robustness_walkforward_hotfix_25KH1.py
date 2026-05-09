from __future__ import annotations

import numpy as np
import pandas as pd

from tradebot.research_hyp003_robustness_walkforward import (
    HYP003_ROBUSTNESS_HOTFIX_VERSION,
    Hyp003CandidateSpec,
    Hyp003RobustnessLimits,
    build_hyp003_robustness_walkforward_report,
    split_walk_forward,
)


def _range_reversion_market(rows: int = 720) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="4h", tz="UTC")
    pattern = [0.0, -0.4, -0.9, -1.5, -2.3, -3.2, -1.1, -0.2, 0.3, 0.8, 1.5, 2.4, 3.2, 1.1, 0.2, -0.2]
    close = np.asarray([100.0 + pattern[idx % len(pattern)] for idx in range(rows)], dtype="float64")
    return pd.DataFrame(
        {
            "timestamp": timestamps.astype("int64") // 1_000_000,
            "open": np.r_[close[0], close[:-1]],
            "high": close + 0.35,
            "low": close - 0.35,
            "close": close,
            "volume": 1000 + np.arange(rows) % 20,
        }
    )


def test_25kh1_declares_hotfix_version() -> None:
    assert HYP003_ROBUSTNESS_HOTFIX_VERSION == "4B.4.3.6.6.25K-H1"


def test_25kh1_walk_forward_keeps_dataframe_chunks() -> None:
    edges = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=12, freq="4h", tz="UTC"),
            "net_edge_bps": [10, 12, 8, 14, 11, 9, 15, 13, 7, 6, 20, 18],
            "side": ["BUY", "SELL"] * 6,
        }
    )
    segments = split_walk_forward(edges, Hyp003RobustnessLimits(min_profit_factor=0.5, min_recent_window_signal_count=1), windows=4)
    assert len(segments) == 4
    assert all(segment.signal_count == 3 for segment in segments)


def test_25kh1_original_robustness_report_no_numpy_chunk_crash() -> None:
    report = build_hyp003_robustness_walkforward_report(
        _range_reversion_market(),
        Hyp003CandidateSpec(hold_bars=2),
        Hyp003RobustnessLimits(
            min_signal_count=20,
            min_recent_window_signal_count=3,
            max_top_win_dependency_pct=70.0,
            min_win_rate_pct=45.0,
        ),
    )
    assert report["decision"] == "HYP003_ROBUSTNESS_PASS", report["reason_codes"]
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
