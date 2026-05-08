from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tradebot.futures_candidate_refinement_median_edge_recovery import (
    BUY_CLASS,
    SELL_CLASS,
    FuturesRefinementSpec,
    MedianEdgeFilterSpec,
    MedianEdgeRecoveryLimits,
    build_futures_candidate_refinement_report,
    derive_spec_from_report,
    evaluate_filtered_signals,
)


def _filtered_edges_df(good: bool = True, n: int = 40) -> pd.DataFrame:
    rows = []
    price = 100.0
    for idx in range(n):
        side = BUY_CLASS if idx % 2 == 0 else SELL_CLASS
        rows.append({"close": price, "refined_signal": True, "base_signal": True, "side": side})
        if good:
            next_price = price * (1.012 if side == BUY_CLASS else 0.988)
        else:
            next_price = price * (0.996 if side == BUY_CLASS else 1.004)
        rows.append({"close": next_price, "refined_signal": False, "base_signal": False, "side": "HOLD"})
        price = 100.0 + (idx % 5) * 0.1
    return pd.DataFrame(rows)


def test_refinement_passes_positive_median_edge_candidate() -> None:
    candidate = evaluate_filtered_signals(
        _filtered_edges_df(good=True, n=40),
        MedianEdgeFilterSpec("median_edge_recovery_guarded"),
        FuturesRefinementSpec(round_trip_cost_bps=16.0),
        MedianEdgeRecoveryLimits(min_signal_count=30, max_coverage_pct=60.0),
    )
    assert candidate["decision"] == "PASS"
    assert candidate["approved_for_research_candidate"] is True
    assert candidate["approved_for_paper_candidate"] is False
    assert candidate["approved_for_live_real"] is False
    assert candidate["metrics"]["median_net_edge_bps"] > 0


def test_refinement_blocks_negative_median_edge_candidate() -> None:
    candidate = evaluate_filtered_signals(
        _filtered_edges_df(good=False, n=40),
        MedianEdgeFilterSpec("median_edge_recovery_guarded"),
        FuturesRefinementSpec(round_trip_cost_bps=16.0),
        MedianEdgeRecoveryLimits(min_signal_count=30),
    )
    assert candidate["decision"] == "BLOCK"
    assert "REFINEMENT_MEDIAN_EDGE_LOW" in candidate["reason_codes"]
    assert candidate["approved_for_live_real"] is False


def test_report_blocks_when_no_filter_passes() -> None:
    df = pd.DataFrame({
        "open": [100, 100.1, 100.2, 100.3] * 40,
        "high": [101, 101, 101, 101] * 40,
        "low": [99, 99, 99, 99] * 40,
        "close": [100, 99.7, 100.1, 99.6] * 40,
        "volume": [1] * 160,
        "fundingRate": [0.00001, -0.00001, 0.00001, -0.00001] * 40,
    })
    report = build_futures_candidate_refinement_report(df, FuturesRefinementSpec())
    assert report["decision"] == "BLOCK"
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_live_real"] is False


def test_derive_spec_from_25d_style_report() -> None:
    report = {"selected": {"symbol": "ETHUSDT", "interval": "4h", "strategy": "funding_trend_exhaustion"}}
    spec = derive_spec_from_report(report)
    assert spec.symbol == "ETHUSDT"
    assert spec.interval == "4h"
    assert spec.strategy == "funding_trend_exhaustion"


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "futures.csv"
    pd.DataFrame({
        "open": [100 + i * 0.01 for i in range(160)],
        "high": [101 + i * 0.01 for i in range(160)],
        "low": [99 + i * 0.01 for i in range(160)],
        "close": [100 + ((-1) ** i) * 0.5 + i * 0.01 for i in range(160)],
        "volume": [10] * 160,
        "fundingRate": [0.0002 if i % 4 < 2 else -0.0002 for i in range(160)],
        "sumOpenInterest": [1000 + i for i in range(160)],
        "buySellRatio": [1.2 if i % 2 == 0 else 0.8 for i in range(160)],
    }).to_csv(csv_path, index=False)
    out_dir = tmp_path / "reports"
    cmd = [
        sys.executable,
        "tools/run_futures_candidate_refinement_median_edge_recovery_4B436625E.py",
        "--input-csv",
        str(csv_path),
        "--symbol",
        "BTCUSDT",
        "--interval",
        "4h",
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    reports = list(out_dir.glob("4B436625E_futures_candidate_refinement_median_edge_recovery_*.json"))
    assert reports
    data = json.loads(reports[0].read_text(encoding="utf-8"))
    assert data["approved_for_paper_candidate"] is False
    assert data["approved_for_live_real"] is False
