from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tradebot.research_hyp005_liquidity_sweep_reversal_exploration import (
    LiquiditySweepExplorationLimits,
    build_hyp005_liquidity_sweep_reversal_exploration_report,
)
from tradebot.research_hyp005_robustness_walkforward import (
    HYP005_ROBUSTNESS_CONTRACT_VERSION,
    Hyp005RobustnessLimits,
    build_hyp005_robustness_walkforward_report,
    selected_spec_from_25s,
    validate_hyp005_25s_report,
)


def _selection_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25R",
        "decision": "NEXT_HYPOTHESIS_SELECTED",
        "selected_next_hypothesis_id": "HYP-005",
        "selected_next_hypothesis_title": "Liquidity sweep reversal with volatility compression filter",
        "selected_next_branch_name": "liquidity_sweep_reversal_vol_compression",
    }


def _synthetic_sweep_frame(symbols: tuple[str, ...] = ("AAAUSDT", "BBBUSDT"), bars: int = 240) -> pd.DataFrame:
    rows: list[dict] = []
    sweep_indices_by_symbol: dict[str, set[int]] = {}
    for sidx, symbol in enumerate(symbols):
        sweep_indices_by_symbol[symbol] = {i for i in range(48, bars - 8, 8) if i % len(symbols) == sidx % len(symbols)}
    for sidx, symbol in enumerate(symbols):
        base = 100.0 + sidx * 25.0
        sweeps = sweep_indices_by_symbol[symbol]
        for i in range(bars):
            trend = i * 0.01
            open_px = base + trend
            close_px = open_px + 0.04
            high_px = close_px + 0.12
            low_px = open_px - 0.12
            if i in sweeps:
                prev_support = base + (i - 24) * 0.01 - 0.12
                low_px = prev_support * 0.990
                close_px = prev_support * 1.007
                open_px = close_px * 0.999
                high_px = close_px * 1.002
            if any((i - j) in sweeps for j in range(1, 7)):
                close_px = max(close_px, base + trend + 1.65)
                open_px = close_px * 0.999
                high_px = close_px * 1.003
                low_px = min(low_px, close_px * 0.997)
            rows.append({
                "symbol": symbol,
                "open_time": i * 14_400_000,
                "open": round(open_px, 6),
                "high": round(max(high_px, open_px, close_px), 6),
                "low": round(min(low_px, open_px, close_px), 6),
                "close": round(close_px, 6),
                "volume": 1000 + i,
            })
    return pd.DataFrame(rows)


def _exploration_pass_report(frame: pd.DataFrame | None = None) -> dict:
    return build_hyp005_liquidity_sweep_reversal_exploration_report(
        frame if frame is not None else _synthetic_sweep_frame(),
        selection_report=_selection_report(),
        source="synthetic",
        limits=LiquiditySweepExplorationLimits(
            min_signal_count=1,
            min_mean_net_edge_bps=0.0,
            min_median_net_edge_bps=0.0,
            min_profit_factor=1.01,
            min_win_rate_pct=40.0,
            min_oos_mean_net_edge_bps=-20.0,
            min_walk_forward_positive_rate_pct=40.0,
            max_dominant_symbol_pct=100.0,
            max_top_win_dependency_pct=100.0,
            min_symbols_traded=1,
        ),
    )


def test_validate_hyp005_25s_pass_report_and_extracts_spec() -> None:
    report = _exploration_pass_report()
    ok, reasons = validate_hyp005_25s_report(report)
    assert ok is True
    assert reasons == []
    spec = selected_spec_from_25s(report)
    assert spec is not None
    assert spec.name == "long_liquidity_sweep_reversal"
    assert HYP005_ROBUSTNESS_CONTRACT_VERSION == "4B.4.3.6.6.25T"


def test_robustness_candidate_can_pass_with_persistent_sweeps() -> None:
    frame = _synthetic_sweep_frame()
    report = build_hyp005_robustness_walkforward_report(
        frame,
        exploration_report=_exploration_pass_report(frame),
        source="synthetic",
        limits=Hyp005RobustnessLimits(
            min_signal_count=1,
            min_mean_net_edge_bps=0.0,
            min_median_net_edge_bps=0.0,
            min_profit_factor=1.01,
            min_win_rate_pct=40.0,
            min_oos_mean_net_edge_bps=-20.0,
            min_walk_forward_positive_rate_pct=40.0,
            max_top_win_dependency_pct=100.0,
            max_dominant_symbol_pct=100.0,
            max_wick_dependency_pct=100.0,
            min_symbols_traded=1,
            min_recent_30d_signal_count=0,
            min_recent_30d_mean_edge_bps=-20.0,
            min_recent_60d_mean_edge_bps=-20.0,
            max_recent_decay_bps=999.0,
            near_floor_signal_count=0,
            small_sample_penalty_bps=0.0,
        ),
    )
    assert report["decision"] == "HYP005_ROBUSTNESS_PASS"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    metrics = report["selected_candidate"]["metrics"]
    assert metrics["signal_count"] >= 1
    assert metrics["symbols_traded"] >= 1


def test_robustness_blocks_when_exploration_not_pass() -> None:
    bad_report = {"decision": "HYP005_EXPLORATION_BLOCK", "hypothesis_id": "HYP-005"}
    report = build_hyp005_robustness_walkforward_report(
        _synthetic_sweep_frame(),
        exploration_report=bad_report,
        source="synthetic",
    )
    assert report["decision"] == "HYP005_ROBUSTNESS_BLOCK"
    assert "HYP005_EXPLORATION_NOT_PASS" in report["reason_codes"]
    assert report["approved_for_live_real"] is False


def test_robustness_applies_small_sample_penalty_and_blocks_weak_sample() -> None:
    frame = _synthetic_sweep_frame(symbols=("AAAUSDT",), bars=70)
    exploration = _exploration_pass_report(_synthetic_sweep_frame())
    report = build_hyp005_robustness_walkforward_report(
        frame,
        exploration_report=exploration,
        source="synthetic-small",
        limits=Hyp005RobustnessLimits(min_signal_count=50, min_symbols_traded=2),
    )
    assert report["decision"] == "HYP005_ROBUSTNESS_BLOCK"
    assert "ROBUST_SIGNAL_COUNT_LOW" in report["reason_codes"]
    assert report["approved_for_research_candidate"] is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "sweeps.csv"
    out_dir = tmp_path / "reports"
    selection_path = tmp_path / "25s.json"
    frame = _synthetic_sweep_frame()
    frame.to_csv(csv_path, index=False)
    selection_path.write_text(json.dumps(_exploration_pass_report(frame)), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp005_robustness_walkforward_4B436625T.py",
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
    assert "HYP-005 robustness/walk-forward" in result.stdout
    assert list(out_dir.glob("4B436625T_hyp005_robustness_walkforward_confirmation_*.json"))
    assert list(out_dir.glob("4B436625T_hyp005_robustness_walkforward_confirmation_*.md"))
