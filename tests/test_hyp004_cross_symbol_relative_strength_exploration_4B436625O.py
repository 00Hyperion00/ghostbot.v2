from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tradebot.research_hyp004_cross_symbol_relative_strength_exploration import (
    CrossSymbolExplorationLimits,
    HYP004_EXPLORATION_CONTRACT_VERSION,
    build_hyp004_cross_symbol_relative_strength_exploration_report,
    validate_hyp004_selection,
)


def _selection_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25N",
        "decision": "NEXT_HYPOTHESIS_SELECTED",
        "selected_next_hypothesis_id": "HYP-004",
        "selected_next_hypothesis_title": "Cross-symbol relative strength rotation",
        "approved_for_research_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def _synthetic_rotation_frame(rows: int = 180) -> pd.DataFrame:
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    prices = {symbol: 100.0 for symbol in symbols}
    records: list[dict] = []
    for i in range(rows):
        leader = symbols[(i // 36) % len(symbols)]
        for symbol in symbols:
            # Persisting relative-strength blocks: leader keeps drifting up; others lag slightly.
            drift = 0.0045 if symbol == leader else (-0.0012 if (i // 12) % 2 == 0 else 0.0004)
            prices[symbol] *= 1.0 + drift
            records.append(
                {
                    "symbol": symbol,
                    "open_time": i * 14_400_000,
                    "open": prices[symbol] * 0.999,
                    "high": prices[symbol] * 1.002,
                    "low": prices[symbol] * 0.998,
                    "close": prices[symbol],
                    "volume": 1000 + i,
                }
            )
    return pd.DataFrame(records)


def test_validate_hyp004_selection_from_25n_report() -> None:
    ok, reasons = validate_hyp004_selection(_selection_report())
    assert ok is True
    assert reasons == []
    bad_ok, bad_reasons = validate_hyp004_selection({"decision": "NEXT_HYPOTHESIS_SELECTED", "selected_next_hypothesis_id": "HYP-003"})
    assert bad_ok is False
    assert "HYP004_NOT_SELECTED" in bad_reasons


def test_relative_strength_candidate_can_pass_with_persistent_rotation() -> None:
    report = build_hyp004_cross_symbol_relative_strength_exploration_report(
        _synthetic_rotation_frame(),
        selection_report=_selection_report(),
        limits=CrossSymbolExplorationLimits(
            min_signal_count=20,
            max_dominant_symbol_pct=75.0,
            max_top_win_dependency_pct=45.0,
            min_walk_forward_positive_rate_pct=50.0,
        ),
    )
    assert report["contract_version"] == HYP004_EXPLORATION_CONTRACT_VERSION
    assert report["decision"] == "HYP004_EXPLORATION_PASS"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["selected_candidate"]["decision"] == "PASS"


def test_report_blocks_when_hyp004_not_selected() -> None:
    report = build_hyp004_cross_symbol_relative_strength_exploration_report(
        _synthetic_rotation_frame(),
        selection_report={"decision": "NEXT_HYPOTHESIS_SELECTED", "selected_next_hypothesis_id": "HYP-003"},
    )
    assert report["decision"] == "HYP004_EXPLORATION_BLOCK"
    assert "HYP004_NOT_SELECTED" in report["reason_codes"]
    assert report["approved_for_live_real"] is False


def test_all_candidates_keep_live_and_paper_blocked() -> None:
    report = build_hyp004_cross_symbol_relative_strength_exploration_report(_synthetic_rotation_frame(), selection_report=_selection_report())
    assert all(candidate["approved_for_paper_candidate"] is False for candidate in report["candidates"])
    assert all(candidate["approved_for_live_real"] is False for candidate in report["candidates"])
    assert report["guardrails"]["post_requests_allowed"] is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "market.csv"
    selection_path = tmp_path / "25n.json"
    out_dir = tmp_path / "reports"
    _synthetic_rotation_frame().to_csv(csv_path, index=False)
    selection_path.write_text(json.dumps(_selection_report()), encoding="utf-8")
    cmd = [
        sys.executable,
        "tools/run_hyp004_cross_symbol_relative_strength_exploration_4B436625O.py",
        "--input-json",
        str(selection_path),
        "--input-csv",
        str(csv_path),
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "approved_for_live_real: False" in result.stdout
    reports = list(out_dir.glob("4B436625O_hyp004_cross_symbol_relative_strength_exploration_*.json"))
    assert reports
    data = json.loads(reports[0].read_text(encoding="utf-8"))
    assert data["approved_for_training_candidate"] is False
    assert data["approved_for_live_real"] is False
