from __future__ import annotations

from tradebot.hyp006_near_miss_outcome_attribution import (
    CONTRACT_VERSION,
    build_near_miss_outcome_attribution_report,
    failed_gate_combo,
    risk_bucket_for_event,
)
from tradebot.hyp006_shadow_runner_dry_run import Candle


def _candles() -> list[Candle]:
    rows: list[Candle] = []
    closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
    for idx, close in enumerate(closes):
        day = 1 + idx
        rows.append(
            Candle(
                timestamp_utc=f"2026-01-{day:02d}T00:00:00+00:00",
                symbol="TESTUSDT",
                open=close + 0.2,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=1000.0,
            )
        )
    return rows


def _h3_payload() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28G-H3",
        "branch_id": "HYP-006-R1",
        "branch_name": "failed_downside_sweep_reversal_continuation_short",
        "read_only": True,
        "runtime_hook_enabled": True,
        "raw_candidate_scan_artifact_found": True,
        "timeframe": "4h",
        "scanned_candle_count": 14,
        "candidate_count": 2,
        "near_miss_count": 2,
        "trigger_count": 1,
        "duplicate_existing_trigger_count": 1,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "symbol_candidate_counter": {"TESTUSDT": 2},
        "symbol_near_miss_counter": {"TESTUSDT": 2},
        "symbol_trigger_counter": {"TESTUSDT": 1},
        "gate_block_counter": {"MIN_WICK_PCT_REFERENCE": 2, "MAX_COMPRESSION_RATIO_REFERENCE": 1},
        "sample_near_miss_events": [
            {
                "timestamp_utc": "2026-01-02T00:00:00+00:00",
                "symbol": "TESTUSDT",
                "timeframe": "4h",
                "failed_gates": ["MIN_WICK_PCT_REFERENCE"],
                "near_miss": True,
                "trigger": False,
                "candidate_probe": True,
                "failed_gate_count": 1,
                "passed_gate_count": 6,
            },
            {
                "timestamp_utc": "2026-01-08T00:00:00+00:00",
                "symbol": "TESTUSDT",
                "timeframe": "4h",
                "failed_gates": ["MAX_COMPRESSION_RATIO_REFERENCE", "MAX_SPREAD_SLIPPAGE_PROXY_BPS"],
                "near_miss": True,
                "trigger": False,
                "candidate_probe": True,
                "failed_gate_count": 2,
                "passed_gate_count": 5,
            },
        ],
    }


def test_gate_combo_and_risk_bucket() -> None:
    event = {"failed_gates": ["MAX_COMPRESSION_RATIO_REFERENCE", "MAX_SPREAD_SLIPPAGE_PROXY_BPS"]}
    assert failed_gate_combo(event) == "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS"
    assert risk_bucket_for_event(event) == "HIGH_COMPRESSION_AND_SLIPPAGE"


def test_build_near_miss_outcome_attribution_report_is_fail_closed() -> None:
    payload = build_near_miss_outcome_attribution_report(h3_artifact=_h3_payload(), candles=_candles(), sample_limit=10)
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["decision"] == "HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_READY"
    assert payload["read_only"] is True
    assert payload["counterfactual_research_only"] is True
    assert payload["attributed_near_miss_event_count"] == 2
    assert payload["matured_near_miss_event_count"] == 2
    assert payload["approved_for_parameter_relaxation_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False
    combos = {row["key"]: row for row in payload["gate_combo_outcome_summary"]}
    assert "MIN_WICK_PCT_REFERENCE" in combos
    assert "MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS" in combos


def test_invalid_h3_source_blocks_report() -> None:
    h3 = _h3_payload()
    h3["contract_version"] = "BAD"
    payload = build_near_miss_outcome_attribution_report(h3_artifact=h3, candles=_candles(), sample_limit=10)
    assert payload["ok"] is False
    assert "SOURCE_H3_CONTRACT_VERSION_MISMATCH" in payload["blockers"]
    assert payload["approved_for_parameter_relaxation_candidate"] is False
