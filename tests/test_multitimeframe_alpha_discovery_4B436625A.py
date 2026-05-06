from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tradebot.multitimeframe_alpha_discovery import (
    MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION,
    MultiTimeframeAlphaCandidate,
    MultiTimeframeAlphaGateLimits,
    analyze_multitimeframe_alpha_candidate,
    build_multitimeframe_alpha_discovery,
)


def make_directional_ohlcv(rows: int = 360) -> pd.DataFrame:
    records: list[dict[str, float]] = []
    close = 100.0
    for i in range(rows):
        block = (i // 30) % 4
        if block == 0:
            drift = 0.45
        elif block == 1:
            drift = 0.02
        elif block == 2:
            drift = -0.45
        else:
            drift = -0.02
        open_price = close
        close = max(1.0, close + drift)
        high = max(open_price, close) + 0.20
        low = min(open_price, close) - 0.20
        volume = 1000.0 + (i % 17) * 20.0
        records.append(
            {
                "open_time": i * 60_000,
                "close_time": i * 60_000 + 59_000,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "quote_volume": volume * close,
            }
        )
    return pd.DataFrame(records)


def test_multitimeframe_alpha_gate_can_pass_directional_research_candidate() -> None:
    df = make_directional_ohlcv()
    candidate = MultiTimeframeAlphaCandidate(
        name="test_15m_directional",
        interval="15m",
        lookahead=4,
        atr_multiplier=0.35,
        cost_bps=0.0,
        min_edge_bps=0.0,
    )
    limits = MultiTimeframeAlphaGateLimits(
        min_samples=100,
        min_action_pct=2.0,
        max_action_pct=95.0,
        min_hold_pct=0.0,
        max_action_side_pct=90.0,
        min_directional_entropy=0.40,
        min_forward_return_gap_bps=-1000.0,
        min_expected_net_edge_bps=-1000.0,
        min_trend_alignment_pct=0.0,
        min_feature_separation_score=-100.0,
        min_class_count=1,
    )
    report = analyze_multitimeframe_alpha_candidate(df, candidate, limits=limits, source="synthetic")
    assert report["contract_version"] == MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION
    assert report["decision"] == "PASS", report
    assert report["approved_for_training_candidate"] is True
    assert report["approved_for_live_real"] is False
    assert report["metrics"]["target_action_pct"] > 0


def test_build_multitimeframe_alpha_discovery_blocks_missing_interval() -> None:
    report = build_multitimeframe_alpha_discovery(
        {"15m": make_directional_ohlcv(220)},
        candidates=[MultiTimeframeAlphaCandidate("missing_5m", "5m", 3, 1.0, 0.0, 0.0)],
        limits=MultiTimeframeAlphaGateLimits(min_samples=20),
        source="synthetic",
    )
    assert report["decision"] == "BLOCK"
    assert "MTF_INTERVAL_DATA_MISSING" in report["reason_codes"]
    assert report["approved_for_paper_candidate"] is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "ohlcv.csv"
    out_dir = tmp_path / "reports"
    make_directional_ohlcv(260).to_csv(csv_path, index=False)
    cmd = [
        sys.executable,
        "tools/run_multitimeframe_alpha_discovery_4B436625A.py",
        "--input-csv",
        str(csv_path),
        "--input-interval",
        "15m",
        "--out-dir",
        str(out_dir),
        "--min-samples",
        "20",
        "--max-candidates",
        "4",
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode in (0, 1), result.stderr
    reports = sorted(out_dir.glob("4B436625A_multitimeframe_alpha_discovery_*.json"))
    assert reports
    payload = json.loads(reports[-1].read_text(encoding="utf-8"))
    assert payload["contract_version"] == MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION
    assert payload["observation_only"] is True
    assert payload["post_requests_allowed"] is False
    assert payload["approved_for_live_real"] is False


def test_tool_requires_review_ok(tmp_path: Path) -> None:
    csv_path = tmp_path / "ohlcv.csv"
    make_directional_ohlcv(120).to_csv(csv_path, index=False)
    cmd = [sys.executable, "tools/run_multitimeframe_alpha_discovery_4B436625A.py", "--input-csv", str(csv_path)]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode == 2
    assert "--review-ok" in result.stderr
