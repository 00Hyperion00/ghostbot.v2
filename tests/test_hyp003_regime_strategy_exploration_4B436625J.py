from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tradebot.research_hyp003_regime_strategy_exploration import (
    HYP003_EXPLORATION_CONTRACT_VERSION,
    RegimeStrategyExplorationLimits,
    build_hyp003_regime_strategy_exploration_report,
    default_strategy_specs,
    evaluate_strategy_candidate,
    validate_hyp003_selected,
)


def _trend_breakout_frame(n: int = 600) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    price = 100.0
    for i in range(n):
        drift = 0.08
        if i % 12 in (4, 5):
            drift = -0.12
        elif i % 12 in (6, 7, 8):
            drift = 0.35
        price = max(1.0, price + drift)
        close = price + 0.05
        open_price = close - 0.03
        rows.append({"open": open_price, "high": close + 0.08, "low": open_price - 0.08, "close": close, "volume": 1000 + i})
    return pd.DataFrame(rows)


def _choppy_negative_frame(n: int = 400) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    price = 100.0
    for i in range(n):
        price += -0.05 if i % 2 else 0.05
        close = price
        rows.append({"open": close, "high": close + 0.1, "low": close - 0.1, "close": close, "volume": 1000})
    return pd.DataFrame(rows)


def _selection_report() -> dict:
    return {"decision": "NEXT_HYPOTHESIS_SELECTED", "selected_next_hypothesis_id": "HYP-003", "selected_next_hypothesis_title": "Regime-specific strategy family"}


def test_validate_hyp003_selection_from_25i_report() -> None:
    ok, reasons = validate_hyp003_selected([_selection_report()])
    assert ok is True
    assert reasons == []


def test_regime_strategy_candidate_can_pass_with_positive_edge() -> None:
    df = _trend_breakout_frame()
    limits = RegimeStrategyExplorationLimits(max_dominant_side_pct=100.0)
    spec = next(item for item in default_strategy_specs() if item.name == "trend_pullback_continuation")
    candidate = evaluate_strategy_candidate(df, symbol="BTCUSDT", interval="1h", spec=spec, limits=limits)
    assert candidate["decision"] == "PASS"
    assert candidate["approved_for_research_candidate"] is True
    assert candidate["approved_for_training_candidate"] is False
    assert candidate["approved_for_paper_candidate"] is False
    assert candidate["approved_for_live_real"] is False
    assert candidate["metrics"]["mean_net_edge_bps"] > 0
    assert candidate["metrics"]["median_net_edge_bps"] > 0


def test_report_blocks_when_hyp003_not_selected() -> None:
    report = build_hyp003_regime_strategy_exploration_report({("BTCUSDT", "1h"): _trend_breakout_frame()}, input_reports=[])
    assert report["decision"] == "HYP003_EXPLORATION_BLOCK"
    assert "HYP003_SELECTION_EVIDENCE_NOT_PROVIDED" in report["reason_codes"]
    assert report["approved_for_live_real"] is False


def test_report_passes_research_only_when_candidate_and_selection_pass() -> None:
    limits = RegimeStrategyExplorationLimits(max_dominant_side_pct=100.0)
    report = build_hyp003_regime_strategy_exploration_report(
        {("BTCUSDT", "1h"): _trend_breakout_frame()},
        input_reports=[_selection_report()],
        limits=limits,
    )
    assert report["contract_version"] == HYP003_EXPLORATION_CONTRACT_VERSION
    assert report["decision"] == "HYP003_EXPLORATION_PASS"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["guardrails"]["post_requests_allowed"] is False


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "trend.csv"
    json_path = tmp_path / "25i.json"
    out_dir = tmp_path / "reports"
    _choppy_negative_frame().to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(_selection_report()), encoding="utf-8")
    cmd = [
        sys.executable,
        "tools/run_hyp003_regime_strategy_exploration_4B436625J.py",
        "--input-json",
        str(json_path),
        "--input-csv",
        f"BTCUSDT:1h:{csv_path}",
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "HYP-003 regime strategy exploration" in result.stdout
    reports = list(out_dir.glob("4B436625J_hyp003_regime_strategy_exploration_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["approved_for_training_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
