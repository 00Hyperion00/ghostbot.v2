from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tradebot.hyp005_shadow_stagnation_diagnostics import (
    CONTRACT_VERSION,
    Candle,
    build_stagnation_diagnostics_report,
    parse_csv_rows,
    stable_observation_id,
    write_json_atomic,
)


def _spec() -> dict[str, object]:
    return {
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "entry_signal_definition": {
            "timeframe": "4h",
            "parameters": {
                "lookback_bars": 3,
                "hold_bars": 2,
                "min_sweep_bps": 20.0,
                "min_wick_pct": 40.0,
                "compression_window": 2,
                "compression_baseline_bars": 3,
                "max_compression_ratio": 2.0,
            },
        },
        "required_shadow_acceptance_metrics": [
            {"name": "min_shadow_sample_target", "threshold": 30},
            {"name": "max_slippage_proxy_bps", "threshold": 12.0},
        ],
    }


def _candle(offset: int, open_: float, high: float, low: float, close: float, symbol: str = "TESTUSDT") -> Candle:
    ts = datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(hours=4 * offset)
    return Candle(ts.isoformat(), symbol, open_, high, low, close, 1000.0)


def _candles() -> list[Candle]:
    rows = [
        _candle(0, 100, 101, 99, 100),
        _candle(1, 100, 101, 99, 100),
        _candle(2, 100, 101, 99, 100),
        _candle(3, 100, 101, 99, 100),
        _candle(4, 98.5, 102, 98, 100.5),  # near miss: wick too low
        _candle(5, 100.5, 101, 99.5, 100.2),
        _candle(6, 100.2, 101, 99.9, 100.3),
        _candle(7, 100, 102, 97, 100.5),  # exact candidate
        _candle(8, 100.5, 101, 100, 100.8),
        _candle(9, 100.8, 101.2, 100.1, 100.9),
    ]
    return rows


def test_contract_version() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.27G-H3"


def test_stagnation_report_counts_duplicate_and_near_miss() -> None:
    duplicate_id = stable_observation_id("TESTUSDT", "4h", _candles()[7].timestamp_utc)
    ledger = [{"observation_id": duplicate_id, "symbol": "TESTUSDT", "timeframe": "4h", "timestamp_utc": _candles()[4].timestamp_utc}]
    report = build_stagnation_diagnostics_report(
        candidate_spec=_spec(),
        ledger_rows=ledger,
        candles=_candles(),
        generated_at="2026-06-15T00:00:00+00:00",
    )
    assert report["ok"] is True
    assert report["decision"] == "HYP005_SHADOW_STAGNATION_DIAGNOSTICS_READY"
    assert report["candidate_diagnostics"]["exact_candidate_count"] >= 1
    assert report["candidate_diagnostics"]["duplicate_candidate_count"] >= 1
    assert report["candidate_diagnostics"]["near_miss_count"] >= 1
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["trading_action_performed"] is False


def test_no_candles_blocks_report_without_side_effect_approval() -> None:
    report = build_stagnation_diagnostics_report(
        candidate_spec=_spec(),
        ledger_rows=[],
        candles=[],
        generated_at="2026-06-15T00:00:00+00:00",
    )
    assert report["ok"] is False
    assert report["decision"] == "HYP005_SHADOW_STAGNATION_DIAGNOSTICS_BLOCK"
    assert report["approved_for_paper_candidate"] is False
    assert report["order_actions_performed"] is False


def test_ascii_json_writer_preserves_unicode_parse_value(tmp_path: Path) -> None:
    target = tmp_path / "Masaüstü" / "rapor.json"
    write_json_atomic(target, {"path": "C:/Users/muhas/OneDrive/Masaüstü/trade_botV2"})
    raw = target.read_text(encoding="utf-8")
    assert "Masa\\u00fcst\\u00fc" in raw
    assert json.loads(raw)["path"].endswith("Masaüstü/trade_botV2")


def test_csv_parser_supports_unicode_path(tmp_path: Path) -> None:
    csv_path = tmp_path / "Masaüstü" / "candles.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "timestamp_utc,symbol,open,high,low,close,volume\n"
        "2026-06-01T00:00:00+00:00,TESTUSDT,1,2,0.5,1.5,100\n",
        encoding="utf-8",
    )
    rows = parse_csv_rows(csv_path)
    assert len(rows) == 1
    assert rows[0].symbol == "TESTUSDT"


def test_stagnation_status_detected_for_old_latest_observation() -> None:
    latest = "2026-06-01T00:00:00+00:00"
    ledger = [{"observation_id": stable_observation_id("AAAUSDT", "4h", latest), "symbol": "AAAUSDT", "timeframe": "4h", "timestamp_utc": latest}]
    report = build_stagnation_diagnostics_report(
        candidate_spec=_spec(),
        ledger_rows=ledger,
        candles=_candles(),
        generated_at="2026-06-15T00:00:00+00:00",
    )
    assert report["stagnation"]["days_since_latest_observation"] >= 14.0
    assert report["stagnation"]["status"] in {"STAGNATED", "DUPLICATE_ONLY", "NEAR_MISS_BOTTLENECK", "NEW_UNIQUE_CANDIDATES_AVAILABLE"}
