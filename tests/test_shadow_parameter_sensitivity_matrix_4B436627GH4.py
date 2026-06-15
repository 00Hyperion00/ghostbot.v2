from __future__ import annotations

from datetime import datetime, timezone, timedelta
from tradebot.hyp005_shadow_parameter_sensitivity import (
    CONTRACT_VERSION,
    build_parameter_sensitivity_report,
    evaluate_sensitivity_matrix,
    threshold_grid,
)
from tradebot.hyp005_shadow_stagnation_diagnostics import Candle, RuntimeSpec, stable_observation_id


def _candles() -> list[Candle]:
    rows: list[Candle] = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for idx in range(80):
        rows.append(
            Candle(
                timestamp_utc=(start + timedelta(hours=4 * idx)).isoformat(),
                symbol="TESTUSDT",
                open=100.4,
                high=101.0,
                low=100.0,
                close=100.5,
                volume=1000.0,
            )
        )
    rows[60] = Candle(
        timestamp_utc="2026-01-11T00:00:00+00:00",
        symbol="TESTUSDT",
        open=100.3,
        high=100.4,
        low=99.85,
        close=100.2,
        volume=2000.0,
    )
    for idx in range(61, 68):
        rows[idx] = Candle(
            timestamp_utc=(start + timedelta(hours=4 * idx)).isoformat(),
            symbol="TESTUSDT",
            open=100.2,
            high=101.2,
            low=100.0,
            close=101.0,
            volume=1000.0,
        )
    return rows


def test_contract_version() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.27G-H4"


def test_threshold_grid_cartesian_product() -> None:
    grid = threshold_grid(min_sweep_bps_values=[18.0, 12.0], min_wick_pct_values=[42.0, 38.0], max_compression_ratio_values=[1.05])
    assert len(grid) == 4
    assert {item["min_sweep_bps"] for item in grid} == {18.0, 12.0}


def test_relaxed_sweep_variant_creates_new_unique_candidate() -> None:
    matrix = evaluate_sensitivity_matrix(
        base_spec=RuntimeSpec(min_sweep_bps=18.0, min_wick_pct=42.0, max_compression_ratio=1.05),
        ledger_rows=[],
        candles=_candles(),
        min_sweep_bps_values=[18.0, 12.0],
        min_wick_pct_values=[42.0],
        max_compression_ratio_values=[1.05],
    )
    relaxed = [row for row in matrix if row["thresholds"]["min_sweep_bps"] == 12.0][0]
    baseline = [row for row in matrix if row["thresholds"]["min_sweep_bps"] == 18.0][0]
    assert relaxed["new_unique_candidate_count"] >= 1
    assert relaxed["delta_vs_baseline"]["new_unique_candidate_delta"] >= 1
    assert baseline["new_unique_candidate_count"] == 0


def test_duplicate_variant_does_not_count_as_new_unique() -> None:
    existing_id = stable_observation_id("TESTUSDT", "4h", "2026-01-11T00:00:00+00:00")
    matrix = evaluate_sensitivity_matrix(
        base_spec=RuntimeSpec(min_sweep_bps=12.0, min_wick_pct=42.0, max_compression_ratio=1.05),
        ledger_rows=[{"observation_id": existing_id, "symbol": "TESTUSDT", "timeframe": "4h", "timestamp_utc": "2026-01-11T00:00:00+00:00"}],
        candles=_candles(),
        min_sweep_bps_values=[12.0],
        min_wick_pct_values=[42.0],
        max_compression_ratio_values=[1.05],
    )
    row = matrix[0]
    assert row["exact_candidate_count"] >= 1
    assert row["duplicate_candidate_count"] >= 1
    assert row["new_unique_candidate_count"] == 0


def test_report_is_fail_closed_research_only() -> None:
    report = build_parameter_sensitivity_report(
        candidate_spec=None,
        ledger_rows=[],
        candles=_candles(),
        min_sweep_bps_values=[18.0, 12.0],
        min_wick_pct_values=[42.0],
        max_compression_ratio_values=[1.05],
        generated_at="2026-01-12T00:00:00+00:00",
    )
    assert report["ok"] is True
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["strategy_parameter_mutation_performed"] is False
    assert report["paper_transition_candidate_found"] is False


def test_report_blocks_without_candles() -> None:
    report = build_parameter_sensitivity_report(candidate_spec=None, ledger_rows=[], candles=[])
    assert report["ok"] is False
    assert report["decision"] == "HYP005_PARAMETER_SENSITIVITY_MATRIX_BLOCK"
    assert report["approved_for_paper_candidate"] is False
