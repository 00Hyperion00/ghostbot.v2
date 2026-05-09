from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradebot.research_hyp005_shadow_observation_logger import (
    HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION,
    Hyp005ShadowRuntimeLimits,
    build_hyp005_shadow_observation_logger_report,
    parse_csv_rows,
    validate_candidate_spec,
)
from tools.run_hyp005_shadow_observation_logger_4B436625V import main as tool_main


def _candidate_spec() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25U",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "status": "NO_ORDER_SHADOW_PLAN_READY",
        "entry_signal_definition": {
            "strategy_family": "long_liquidity_sweep_reversal",
            "timeframe": "4h",
            "execution_mode": "NO_ORDER_SHADOW_ONLY",
            "parameters": {
                "lookback_bars": 24,
                "hold_bars": 6,
                "min_sweep_bps": 18.0,
                "min_wick_pct": 42.0,
                "compression_window": 12,
                "compression_baseline_bars": 30,
                "max_compression_ratio": 1.05,
            },
        },
        "risk_observation_fields": [
            "timestamp_utc",
            "symbol",
            "timeframe",
            "strategy_family",
            "sweep_direction",
            "lookback_low",
            "swept_low",
            "sweep_depth_bps",
            "wick_pct",
            "compression_ratio",
            "entry_reference_price",
            "invalidation_level",
            "hold_horizon_bars",
            "forward_return_bps_h1",
            "forward_return_bps_h2",
            "forward_return_bps_h3",
            "forward_return_bps_final",
            "mae_bps",
            "mfe_bps",
            "spread_slippage_proxy_bps",
            "volume_context",
            "regime_context",
            "data_quality_ok",
            "operator_review_status",
        ],
        "guardrails": {
            "observation_only": True,
            "no_order_shadow_only": True,
            "orders_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "training_allowed": False,
            "model_reload_allowed": False,
            "config_mutation_allowed": False,
            "post_requests_allowed": False,
            "manual_review_required": True,
            "paper_transition_requires_new_gate": True,
            "live_transition_requires_separate_gate": True,
        },
    }


def _write_signal_csv(path: Path) -> None:
    rows: list[dict[str, object]] = []
    for idx in range(40):
        rows.append({
            "timestamp_utc": f"2026-01-{1 + idx // 6:02d}T{(idx % 6) * 4:02d}:00:00+00:00",
            "symbol": "BTCUSDT",
            "open": 101.0,
            "high": 102.0,
            "low": 100.0,
            "close": 101.0,
            "volume": 1000 + idx,
        })
    rows.append({
        "timestamp_utc": "2026-01-08T00:00:00+00:00",
        "symbol": "BTCUSDT",
        "open": 101.0,
        "high": 101.8,
        "low": 99.0,
        "close": 100.7,
        "volume": 2000,
    })
    future_closes = [101.2, 101.6, 102.0, 102.2, 102.8, 103.0, 103.4]
    for offset, close in enumerate(future_closes, start=1):
        rows.append({
            "timestamp_utc": f"2026-01-08T{offset * 4:02d}:00:00+00:00",
            "symbol": "BTCUSDT",
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.4,
            "close": close,
            "volume": 1500 + offset,
        })
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_25v_validates_no_order_candidate_spec() -> None:
    runtime_spec, reasons, warnings = validate_candidate_spec(_candidate_spec())
    assert HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION == "4B.4.3.6.6.25V"
    assert reasons == []
    assert runtime_spec is not None
    assert runtime_spec.no_order_shadow_only is True
    assert runtime_spec.orders_allowed is False
    assert runtime_spec.paper_transition_requires_new_gate is True


def test_25v_detects_shadow_liquidity_sweep_observation(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    _write_signal_csv(csv_path)
    candles = parse_csv_rows(csv_path)
    report = build_hyp005_shadow_observation_logger_report(
        candidate_spec=_candidate_spec(),
        candles=candles,
        symbols=["BTCUSDT"],
        timeframe="4h",
        limits=Hyp005ShadowRuntimeLimits(min_shadow_sample_target=1, min_rows_per_symbol=20),
    )
    assert report["decision"] == "HYP005_SHADOW_OBSERVATION_LOGGER_READY"
    assert report["approved_for_shadow_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["shadow_observation_count"] >= 1
    first = report["shadow_observations"][0]
    assert first["order_action"] == "NONE"
    assert first["no_order_shadow_only"] is True
    assert first["forward_return_bps_final"] is not None


def test_25v_blocks_when_spec_allows_orders() -> None:
    spec = _candidate_spec()
    spec["guardrails"]["orders_allowed"] = True
    report = build_hyp005_shadow_observation_logger_report(candidate_spec=spec, candles=[], symbols=["BTCUSDT"])
    assert report["decision"] == "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK"
    assert "SPEC_ORDERS_ALLOWED_GUARDRAIL_VIOLATION" in report["reason_codes"]
    assert report["approved_for_paper_candidate"] is False


def test_tool_writes_report_and_ledger_files(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    csv_path = tmp_path / "candles.csv"
    out_dir = tmp_path / "reports"
    spec_path.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    _write_signal_csv(csv_path)
    rc = tool_main([
        "--candidate-spec-json",
        str(spec_path),
        "--input-csv",
        str(csv_path),
        "--symbols",
        "BTCUSDT",
        "--interval",
        "4h",
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ])
    assert rc == 0
    reports = list(out_dir.glob("4B436625V_hyp005_shadow_observation_logger_*.json"))
    ledgers = list(out_dir.glob("4B436625V_hyp005_shadow_observation_ledger_*.json"))
    ledger_jsonls = list(out_dir.glob("4B436625V_hyp005_shadow_observation_ledger_*.jsonl"))
    assert len(reports) == 1
    assert len(ledgers) == 1
    assert len(ledger_jsonls) == 1
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    ledger = json.loads(ledgers[0].read_text(encoding="utf-8"))
    assert report["decision"] == "HYP005_SHADOW_OBSERVATION_LOGGER_READY"
    assert report["ledger_json"] == str(ledgers[0])
    assert report["ledger_jsonl"] == str(ledger_jsonls[0])
    assert isinstance(ledger, list)
    assert report["guardrails"]["orders_allowed"] is False


def test_tool_requires_review_ok(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    rc = tool_main(["--candidate-spec-json", str(spec_path), "--symbols", "BTCUSDT"])
    assert rc == 2
