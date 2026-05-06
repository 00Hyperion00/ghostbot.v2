from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from tradebot.regime_aware_edge_filter_recovery import (
    REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION,
    RegimeFilterCandidate,
    build_regime_edge_filter_report,
    build_report_from_two_stage_json,
    evaluate_regime_filter_candidate,
)

_PATTERN_N = 80
_PATTERN_LEN = 20


def _features() -> pd.DataFrame:
    mtf = [1, 1, -1, -1] + [0] * 16
    mtf_gap = [0.1, 0.1, -0.1, -0.1] + [0.0] * 16
    ema = [0.1, 0.1, -0.1, -0.1] + [0.0] * 16
    vwap = [0.2, 0.2, -0.2, -0.2] + [0.0] * 16
    close_loc = [0.7, 0.7, 0.3, 0.3] + [0.5] * 16
    n = _PATTERN_N * _PATTERN_LEN
    return pd.DataFrame(
        {
            "mtf_15m_trend_flag": mtf * _PATTERN_N,
            "mtf_15m_ema_gap_pct": mtf_gap * _PATTERN_N,
            "ema_spread_pct": ema * _PATTERN_N,
            "close_to_vwap_pct": vwap * _PATTERN_N,
            "vwap_distance_atr_norm": vwap * _PATTERN_N,
            "volume": list(range(n)),
            "atr_pct": [0.01] * n,
            "range_regime_flag": [0] * n,
            "volatility_regime_flag": [1] * n,
            "trend_strength_proxy": [0.2] * n,
            "RSI_14": ([55, 56, 45, 44] + [50] * 16) * _PATTERN_N,
            "close_location_pct": close_loc * _PATTERN_N,
        }
    )


def _actual_staged_good() -> tuple[list[int], list[int]]:
    actual_pattern = [1, 1, 2, 2] + [0] * 16
    staged_pattern = [1, 1, 2, 2] + [0] * 12 + [1, 2, 1, 2]
    return actual_pattern * _PATTERN_N, staged_pattern * _PATTERN_N


def _actual_staged_bad() -> tuple[list[int], list[int]]:
    actual_pattern = [2, 2, 1, 1] + [0] * 16
    staged_pattern = [1, 1, 2, 2] + [0] * 12 + [1, 2, 1, 2]
    return actual_pattern * _PATTERN_N, staged_pattern * _PATTERN_N


def test_regime_filter_gate_passes_positive_edge_filter() -> None:
    actual, staged = _actual_staged_good()
    result = evaluate_regime_filter_candidate(
        candidate=RegimeFilterCandidate("mtf_trend_aligned", "trend", "aligned"),
        actual=actual,
        staged_pred=staged,
        features=_features(),
        baseline_action_precision=0.20,
        effective_min_profit_bps=40.0,
    )
    assert result["contract_version"] == REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION
    assert result["decision"] == "PASS"
    assert result["metrics"]["expected_edge_proxy_bps"] > 0
    assert result["approved_for_live_real"] is False


def test_regime_filter_blocks_negative_edge_filter() -> None:
    actual, staged = _actual_staged_bad()
    result = evaluate_regime_filter_candidate(
        candidate=RegimeFilterCandidate("mtf_trend_aligned", "trend", "aligned"),
        actual=actual,
        staged_pred=staged,
        features=_features(),
        baseline_action_precision=0.20,
        effective_min_profit_bps=40.0,
    )
    assert result["decision"] == "BLOCK"
    assert "REGIME_FILTER_EXPECTED_EDGE_LOW" in result["reason_codes"]


def test_aggregate_24k_json_is_not_approvable() -> None:
    report = build_report_from_two_stage_json(
        {
            "contract_version": "4B.4.3.6.6.24K",
            "decision": "BLOCK",
            "selected_action_precision": 0.165,
            "selected_side_accuracy": 0.615,
            "selected_expected_edge_proxy_bps": -13.9,
        }
    )
    assert report["decision"] == "BLOCK"
    assert "REGIME_SAMPLE_FEATURES_MISSING" in report["reason_codes"]
    assert report["approved_for_live_real"] is False


def test_report_selects_pass_candidate() -> None:
    actual, staged = _actual_staged_good()
    candidate = evaluate_regime_filter_candidate(
        candidate=RegimeFilterCandidate("mtf_trend_aligned", "trend", "aligned"),
        actual=actual,
        staged_pred=staged,
        features=_features(),
        baseline_action_precision=0.20,
        effective_min_profit_bps=40.0,
    )
    report = build_regime_edge_filter_report([candidate], source="unit")
    assert report["decision"] == "PASS"
    assert report["approved_for_paper_candidate"] is False
    assert report["guardrails"]["post_requests_allowed"] is False


def test_tool_writes_report_from_candidate_json(tmp_path: Path) -> None:
    payload = {"contract_version": "4B.4.3.6.6.24K", "decision": "BLOCK", "selected_expected_edge_proxy_bps": -10.0}
    input_path = tmp_path / "24k.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    out_dir = tmp_path / "reports"
    script = Path(__file__).resolve().parents[1] / "tools" / "run_regime_aware_edge_filter_recovery_4B436624L.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--input-json", str(input_path), "--out-dir", str(out_dir)],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "regime-aware edge filter recovery BLOCK" in completed.stdout
    assert list(out_dir.glob("4B436624L_regime_aware_edge_filter_recovery_*.json"))
