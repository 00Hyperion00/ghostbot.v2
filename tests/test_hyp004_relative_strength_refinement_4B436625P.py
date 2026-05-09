from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tradebot.research_hyp004_relative_strength_refinement import (
    HYP004_REFINEMENT_CONTRACT_VERSION,
    RelativeStrengthRefinementLimits,
    RelativeStrengthRefinementSpec,
    build_hyp004_relative_strength_refinement_report,
    validate_hyp004_25o_report,
)


def _selection_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25O",
        "decision": "HYP004_EXPLORATION_BLOCK",
        "hypothesis_id": "HYP-004",
        "selected_candidate": {"strategy_family": "laggard_reversion"},
        "reason_codes": ["NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED"],
    }


def _cyclic_market(rows: int = 240) -> pd.DataFrame:
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    frames: list[dict[str, float | int | str]] = []
    phases = np.linspace(0, 2 * np.pi, len(symbols), endpoint=False)
    for t in range(rows):
        for symbol, phase in zip(symbols, phases):
            # Phase-shifted oscillation creates repeated relative laggard reversion.
            price = 100.0 * np.exp(0.0002 * t + 0.055 * np.sin(2 * np.pi * t / 24.0 + phase))
            frames.append({
                "symbol": symbol,
                "open_time": t,
                "open": price,
                "high": price * 1.002,
                "low": price * 0.998,
                "close": price,
                "volume": 1000.0,
            })
    return pd.DataFrame(frames)


def test_validate_hyp004_25o_report_accepts_laggard_reversion_selection() -> None:
    ok, reasons, selected_family = validate_hyp004_25o_report(_selection_report())
    assert ok is True
    assert reasons == []
    assert selected_family == "laggard_reversion"


def test_refined_candidate_can_pass_with_persistent_relative_reversion() -> None:
    report = build_hyp004_relative_strength_refinement_report(
        _cyclic_market(),
        exploration_report=_selection_report(),
        specs=(
            RelativeStrengthRefinementSpec(
                name="test_laggard_reversion_cycle",
                lookback_bars=6,
                hold_bars=6,
                min_spread_bps=40.0,
                min_laggard_underperformance_bps=5.0,
            ),
        ),
        limits=RelativeStrengthRefinementLimits(
            min_signal_count=20,
            min_mean_net_edge_bps=5.0,
            min_median_net_edge_bps=5.0,
            min_profit_factor=1.1,
            min_win_rate_pct=45.0,
            min_oos_mean_net_edge_bps=0.0,
            min_walk_forward_positive_rate_pct=50.0,
            max_dominant_symbol_pct=80.0,
            max_top_win_dependency_pct=80.0,
            min_symbols_traded=2,
            round_trip_cost_bps=1.0,
        ),
        generated_at="2026-05-09T00:00:00+00:00",
    )
    assert report["decision"] == "HYP004_REFINEMENT_PASS"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["next_candidate_spec"] is not None


def test_refinement_blocks_when_25o_selected_family_is_not_laggard_reversion() -> None:
    selection = _selection_report()
    selection["selected_candidate"] = {"strategy_family": "leader_long_momentum"}
    report = build_hyp004_relative_strength_refinement_report(
        _cyclic_market(80),
        exploration_report=selection,
        specs=(RelativeStrengthRefinementSpec(name="test", lookback_bars=6, hold_bars=6),),
        limits=RelativeStrengthRefinementLimits(min_signal_count=1, min_mean_net_edge_bps=-999, min_median_net_edge_bps=-999, min_profit_factor=0, min_win_rate_pct=0, min_oos_mean_net_edge_bps=-999, min_walk_forward_positive_rate_pct=0, max_dominant_symbol_pct=100, max_top_win_dependency_pct=100, min_symbols_traded=1),
    )
    assert report["decision"] == "HYP004_REFINEMENT_BLOCK"
    assert "HYP004_SELECTED_FAMILY_NOT_LAGGARD_REVERSION" in report["reason_codes"]


def test_refinement_keeps_all_live_permissions_blocked() -> None:
    report = build_hyp004_relative_strength_refinement_report(_cyclic_market(80), exploration_report=_selection_report())
    assert report["contract_version"] == HYP004_REFINEMENT_CONTRACT_VERSION
    assert report["post_requests_allowed"] is False
    assert report["config_mutation_performed"] is False
    assert report["order_actions_performed"] is False
    assert report["reload_performed"] is False
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "market.csv"
    input_json = tmp_path / "25o.json"
    out_dir = tmp_path / "reports"
    _cyclic_market(100).to_csv(csv_path, index=False)
    input_json.write_text(json.dumps(_selection_report()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp004_relative_strength_refinement_4B436625P.py",
            "--input-json",
            str(input_json),
            "--input-csv",
            str(csv_path),
            "--symbols",
            "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT",
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
    reports = list(out_dir.glob("4B436625P_hyp004_relative_strength_refinement_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["approved_for_training_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
