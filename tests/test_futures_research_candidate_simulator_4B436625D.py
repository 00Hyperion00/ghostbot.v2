from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tradebot.futures_research_candidate_simulator import (
    FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION,
    DryRunSimulatorLimits,
    FuturesResearchCandidateSpec,
    build_candidate_spec_from_robustness_report,
    build_futures_research_candidate_simulator_report,
    evaluate_dry_run_candidate,
)


def _synthetic_futures_frame(*, positive_edge: bool = True, cycles: int = 44) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []
    ts = 1_700_000_000_000
    price = 100.0
    for cycle in range(cycles):
        sell_cycle = cycle % 2 == 0
        # Warm trend bars create EMA alignment.
        drift = 0.45 if sell_cycle else -0.45
        for _ in range(5):
            open_price = price
            close_price = price + drift
            rows.append({
                "timestamp": ts,
                "open": open_price,
                "high": max(open_price, close_price) + 0.15,
                "low": min(open_price, close_price) - 0.15,
                "close": close_price,
                "volume": 1000,
                "fundingRate": 0.00002,
                "sumOpenInterest": 1000000 + cycle,
                "longShortRatio": 1.0,
                "buySellRatio": 1.0,
            })
            price = close_price
            ts += 4 * 60 * 60 * 1000
        signal_funding = 0.0015 if sell_cycle else -0.0015
        rows.append({
            "timestamp": ts,
            "open": price,
            "high": price + 0.3,
            "low": price - 0.3,
            "close": price,
            "volume": 1400,
            "fundingRate": signal_funding,
            "sumOpenInterest": 1000000 + cycle,
            "longShortRatio": 1.0,
            "buySellRatio": 1.0,
        })
        ts += 4 * 60 * 60 * 1000
        # Post-signal path: favourable when positive_edge=True, adverse otherwise.
        move = -1.4 if sell_cycle else 1.4
        if not positive_edge:
            move = -move
        for _ in range(4):
            open_price = price
            close_price = price + move
            rows.append({
                "timestamp": ts,
                "open": open_price,
                "high": max(open_price, close_price) + 0.15,
                "low": min(open_price, close_price) - 0.15,
                "close": close_price,
                "volume": 1200,
                "fundingRate": 0.00002,
                "sumOpenInterest": 1000000 + cycle,
                "longShortRatio": 1.0,
                "buySellRatio": 1.0,
            })
            price = close_price
            ts += 4 * 60 * 60 * 1000
    return pd.DataFrame(rows)


def test_dry_run_simulator_passes_positive_futures_candidate() -> None:
    df = _synthetic_futures_frame(positive_edge=True, cycles=60)
    spec = FuturesResearchCandidateSpec(symbol="BTCUSDT", interval="4h", strategy="funding_trend_exhaustion", hold_bars=3)
    result = evaluate_dry_run_candidate(df, spec)
    assert result.decision == "PASS"
    assert result.approved_for_research_candidate is True
    assert result.approved_for_paper_candidate is False
    assert result.approved_for_live_real is False
    assert result.metrics["signal_count"] >= 30
    assert result.metrics["mean_net_edge_bps"] > 0
    assert result.metrics["profit_factor"] >= 1.15


def test_dry_run_simulator_blocks_negative_edge_candidate() -> None:
    df = _synthetic_futures_frame(positive_edge=False, cycles=60)
    spec = FuturesResearchCandidateSpec(symbol="BTCUSDT", interval="4h", strategy="funding_trend_exhaustion", hold_bars=3)
    result = evaluate_dry_run_candidate(df, spec)
    assert result.decision == "BLOCK"
    assert result.reason_codes
    assert result.approved_for_paper_candidate is False
    assert result.approved_for_live_real is False


def test_candidate_spec_from_25c_report_prefers_selected_candidate() -> None:
    report = {
        "selected": {"symbol": "BTCUSDT", "interval": "4h", "strategy": "funding_trend_exhaustion"},
        "candidates": [
            {"decision": "PASS", "symbol": "BTCUSDT", "interval": "4h", "strategy": "funding_trend_exhaustion"},
            {"decision": "PASS", "symbol": "ETHUSDT", "interval": "4h", "strategy": "funding_trend_exhaustion"},
        ],
    }
    spec = build_candidate_spec_from_robustness_report(report)
    assert spec.symbol == "BTCUSDT"
    assert spec.interval == "4h"
    assert spec.strategy == "funding_trend_exhaustion"
    assert "ETHUSDT" in spec.comparator_symbols


def test_report_preserves_guardrails() -> None:
    df = _synthetic_futures_frame(positive_edge=True, cycles=60)
    spec = FuturesResearchCandidateSpec(symbol="BTCUSDT", interval="4h", strategy="funding_trend_exhaustion", hold_bars=3)
    report = build_futures_research_candidate_simulator_report(df, spec, "synthetic")
    assert report.contract_version == FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION
    assert report.guardrails["post_requests_allowed"] is False
    assert report.guardrails["reload_performed"] is False
    assert report.guardrails["live_real_allowed"] is False
    assert report.approved_for_training_candidate is False
    assert report.approved_for_paper_candidate is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "candidate.csv"
    _synthetic_futures_frame(positive_edge=True, cycles=60).to_csv(csv_path, index=False)
    out_dir = tmp_path / "reports"
    cmd = [
        sys.executable,
        "tools/run_futures_research_candidate_simulator_4B436625D.py",
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
    completed = subprocess.run(cmd, cwd=Path.cwd(), text=True, capture_output=True, check=True)
    assert "futures dry-run signal simulator" in completed.stdout
    reports = list(out_dir.glob("4B436625D_futures_research_candidate_simulator_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
