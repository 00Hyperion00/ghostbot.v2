from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tradebot.research_hyp005_liquidity_sweep_reversal_exploration import (
    HYP005_EXPLORATION_CONTRACT_VERSION,
    LiquiditySweepExplorationLimits,
    build_hyp005_liquidity_sweep_reversal_exploration_report,
    validate_hyp005_selection,
)


def _selection_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25R",
        "decision": "NEXT_HYPOTHESIS_SELECTED",
        "selected_next_hypothesis_id": "HYP-005",
        "selected_next_hypothesis_title": "Liquidity sweep reversal with volatility compression filter",
        "selected_next_branch_name": "liquidity_sweep_reversal_vol_compression",
    }


def _synthetic_sweep_frame(symbols: tuple[str, ...] = ("AAAUSDT", "BBBUSDT"), bars: int = 180) -> pd.DataFrame:
    rows: list[dict] = []
    for sidx, symbol in enumerate(symbols):
        base = 100.0 + sidx * 20.0
        for i in range(bars):
            trend = i * 0.015
            open_px = base + trend
            close_px = open_px + 0.05
            high_px = max(open_px, close_px) + 0.18
            low_px = min(open_px, close_px) - 0.18
            # Regular long sweep every 7 bars after the lookback is available.
            if i >= 42 and i % 7 == (sidx % 3):
                prev_support = base + (i - 24) * 0.015 - 0.18
                low_px = prev_support * 0.992
                close_px = prev_support * 1.006
                open_px = close_px * 0.999
                high_px = close_px * 1.002
            # Give sweep bars positive future follow-through within hold window.
            if i >= 42 and any((i - j) >= 42 and (i - j) % 7 == (sidx % 3) for j in range(1, 7)):
                close_px = max(close_px, base + trend + 1.15)
                open_px = close_px * 0.999
                high_px = close_px * 1.003
                low_px = min(low_px, close_px * 0.997)
            rows.append(
                {
                    "symbol": symbol,
                    "open_time": i * 14_400_000,
                    "open": round(open_px, 6),
                    "high": round(max(high_px, open_px, close_px), 6),
                    "low": round(min(low_px, open_px, close_px), 6),
                    "close": round(close_px, 6),
                    "volume": 1000 + i,
                }
            )
    return pd.DataFrame(rows)


def test_validate_hyp005_selection_from_25r_report() -> None:
    ok, reasons = validate_hyp005_selection(_selection_report())
    assert ok is True
    assert reasons == []
    assert HYP005_EXPLORATION_CONTRACT_VERSION == "4B.4.3.6.6.25S"


def test_liquidity_sweep_candidate_can_pass_with_reversal_edges() -> None:
    report = build_hyp005_liquidity_sweep_reversal_exploration_report(
        _synthetic_sweep_frame(),
        selection_report=_selection_report(),
        source="synthetic",
        limits=LiquiditySweepExplorationLimits(
            min_signal_count=2,
            min_mean_net_edge_bps=0.0,
            min_median_net_edge_bps=0.0,
            min_profit_factor=1.05,
            min_win_rate_pct=45.0,
            min_oos_mean_net_edge_bps=0.0,
            min_walk_forward_positive_rate_pct=50.0,
            max_dominant_symbol_pct=80.0,
            max_top_win_dependency_pct=100.0,
            min_symbols_traded=2,
        ),
    )
    assert report["decision"] == "HYP005_EXPLORATION_PASS"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    selected = report["selected_candidate"]
    assert selected["decision"] == "PASS"
    assert selected["metrics"]["signal_count"] >= 2
    assert selected["metrics"]["symbols_traded"] >= 2


def test_exploration_blocks_when_hyp005_not_selected() -> None:
    bad_selection = {"decision": "NEXT_HYPOTHESIS_SELECTED", "selected_next_hypothesis_id": "HYP-999"}
    report = build_hyp005_liquidity_sweep_reversal_exploration_report(
        _synthetic_sweep_frame(),
        selection_report=bad_selection,
        source="synthetic",
    )
    assert report["decision"] == "HYP005_EXPLORATION_BLOCK"
    assert "HYP005_NOT_SELECTED" in report["reason_codes"]
    assert report["approved_for_live_real"] is False


def test_diagnostic_probe_never_approves_if_selected_best() -> None:
    report = build_hyp005_liquidity_sweep_reversal_exploration_report(
        _synthetic_sweep_frame(symbols=("AAAUSDT",), bars=80),
        selection_report=_selection_report(),
        source="synthetic-small",
        limits=LiquiditySweepExplorationLimits(min_signal_count=999, min_symbols_traded=2),
    )
    assert report["decision"] == "HYP005_EXPLORATION_BLOCK"
    assert report["approved_for_research_candidate"] is False
    assert "NO_HYP005_LIQUIDITY_SWEEP_CANDIDATE_PASSED" in report["reason_codes"]


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "sweeps.csv"
    out_dir = tmp_path / "reports"
    selection_path = tmp_path / "25r.json"
    _synthetic_sweep_frame().to_csv(csv_path, index=False)
    selection_path.write_text(json.dumps(_selection_report()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp005_liquidity_sweep_reversal_exploration_4B436625S.py",
            "--input-json",
            str(selection_path),
            "--input-csv",
            str(csv_path),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "HYP-005 liquidity sweep reversal exploration" in result.stdout
    assert list(out_dir.glob("4B436625S_hyp005_liquidity_sweep_reversal_exploration_*.json"))
    assert list(out_dir.glob("4B436625S_hyp005_liquidity_sweep_reversal_exploration_*.md"))
