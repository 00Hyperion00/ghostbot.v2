from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tradebot.research_hyp005_shadow_acceptance_readiness import (
    HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION,
    build_hyp005_shadow_acceptance_report,
    load_observations_from_paths,
    summarize_shadow_observations,
    write_json,
)


def make_observations(count: int = 32) -> list[dict[str, object]]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    rows: list[dict[str, object]] = []
    for idx in range(count):
        edge = 95.0 + (idx % 5) * 7.0
        if idx in {7, 19}:
            edge = -18.0
        rows.append(
            {
                "timestamp_utc": (start + timedelta(days=idx)).isoformat(),
                "symbol": symbols[idx % len(symbols)],
                "timeframe": "4h",
                "strategy_family": "long_liquidity_sweep_reversal",
                "sweep_direction": "LONG_REVERSAL",
                "lookback_low": 100.0,
                "swept_low": 99.2,
                "sweep_depth_bps": 80.0,
                "wick_pct": 44.0,
                "compression_ratio": 0.82,
                "entry_reference_price": 101.0,
                "invalidation_level": 98.8,
                "forward_return_bps_final": edge,
                "mae_bps": -22.0,
                "mfe_bps": edge + 35.0,
                "spread_slippage_proxy_bps": 5.0,
                "data_quality_ok": True,
                "operator_review_status": "REVIEWED",
                "no_order_shadow_only": True,
                "order_action": "NONE",
            }
        )
    return rows


def test_25w_declares_contract_version() -> None:
    assert HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION == "4B.4.3.6.6.25W"


def test_25w_blocks_empty_shadow_ledger() -> None:
    report = build_hyp005_shadow_acceptance_report(observations=[], source_ledgers=["empty.json"])
    assert report["decision"] == "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"
    assert report["paper_transition_ready"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert "SHADOW_SAMPLE_COUNT_LOW" in report["reason_codes"]
    assert "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED" not in report["reason_codes"]


def test_25w_accepts_strong_shadow_ledger_but_keeps_paper_live_blocked() -> None:
    report = build_hyp005_shadow_acceptance_report(observations=make_observations(), source_ledgers=["strong.json"])
    summary = report["shadow_acceptance_summary"]
    assert report["decision"] == "HYP005_SHADOW_PAPER_TRANSITION_READY"
    assert report["paper_transition_ready"] is True
    assert report["approved_for_paper_transition_candidate"] is True
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["guardrails"]["orders_allowed"] is False
    assert report["guardrails"]["paper_trading_allowed"] is False
    assert summary["shadow_observation_count"] >= 30
    assert summary["shadow_profit_factor"] >= 1.5
    assert "PAPER_TRANSITION_READY_REQUIRES_SEPARATE_ENABLEMENT" in report["reason_codes"]


def test_25w_loads_json_and_jsonl_ledgers(tmp_path: Path) -> None:
    rows = make_observations(4)
    json_path = tmp_path / "ledger.json"
    jsonl_path = tmp_path / "ledger.jsonl"
    write_json(json_path, rows[:2])
    jsonl_path.write_text("\n".join(json.dumps(row) for row in rows[2:]) + "\n", encoding="utf-8")
    loaded, sources = load_observations_from_paths([json_path, jsonl_path])
    summary = summarize_shadow_observations(loaded)
    assert len(loaded) == 4
    assert str(json_path) in sources
    assert str(jsonl_path) in sources
    assert summary.shadow_signal_capture_count == 4


def test_tool_writes_report_and_summary_from_ledger_json(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    out_dir = tmp_path / "reports"
    write_json(ledger, make_observations())
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py",
            "--ledger-json",
            str(ledger),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "HYP005_SHADOW_PAPER_TRANSITION_READY" in result.stdout
    reports = list(out_dir.glob("4B436625W_hyp005_shadow_observation_acceptance_*.json"))
    summaries = list(out_dir.glob("4B436625W_hyp005_shadow_acceptance_summary_*.json"))
    assert reports
    assert summaries
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["approved_for_paper_transition_candidate"] is True
    assert payload["approved_for_paper_candidate"] is False
