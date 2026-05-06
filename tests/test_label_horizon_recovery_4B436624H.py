from __future__ import annotations

import json
import math
import importlib.util
import sys
from pathlib import Path

import pandas as pd

from tradebot.label_horizon_recovery import (
    LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
    LabelHorizonGateLimits,
    LabelPolicyCandidate,
    build_label_horizon_recovery,
)


def _synthetic_ohlcv(rows: int = 1800, *, mode: str = "oscillating") -> pd.DataFrame:
    close = []
    price = 100.0
    for i in range(rows):
        if mode == "up_only":
            step = 0.035 + 0.005 * math.sin(i / 13.0)
        else:
            # Long enough directional waves for ATR barrier labels to produce both BUY and SELL.
            wave = math.sin(i / 18.0)
            step = 0.11 * (1.0 if wave >= 0 else -1.0) + 0.015 * math.sin(i / 5.0)
        price = max(10.0, price + step)
        close.append(price)
    out = pd.DataFrame({"close": close})
    out["open"] = out["close"].shift(1).fillna(out["close"])
    spread = 0.10 if mode != "up_only" else 0.05
    out["high"] = out[["open", "close"]].max(axis=1) + spread
    out["low"] = out[["open", "close"]].min(axis=1) - spread
    out["volume"] = 100 + (pd.Series(range(rows)) % 25) * 3
    out["quote_volume"] = out["volume"] * out["close"]
    out["open_time"] = pd.Series(range(rows), dtype="int64") * 60_000
    out["close_time"] = out["open_time"] + 59_999
    return out[["open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"]]


def _load_tool_module():
    script = Path(__file__).resolve().parents[1] / "tools" / "run_label_horizon_recovery_4B436624H.py"
    spec = importlib.util.spec_from_file_location("run_label_horizon_recovery_4B436624H", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_label_horizon_gate_passes_balanced_directional_policy() -> None:
    df = _synthetic_ohlcv(300)
    limits = LabelHorizonGateLimits(
        min_samples=50,
        min_action_pct=2.0,
        max_action_pct=100.0,
        min_hold_pct=0.0,
        max_hold_pct=95.0,
        max_action_side_pct=90.0,
        min_directional_entropy=0.40,
        min_forward_return_gap_bps=1.0,
        min_buy_direction_consistency_pct=45.0,
        min_sell_direction_consistency_pct=45.0,
        min_class_count=5,
    )
    policies = [LabelPolicyCandidate("test_h5_atr0_6", lookahead=5, atr_multiplier=0.6)]
    report = build_label_horizon_recovery(df, policies=policies, limits=limits)
    assert report["contract_version"] == LABEL_HORIZON_RECOVERY_CONTRACT_VERSION
    assert report["decision"] == "PASS"
    assert report["approved_for_training_candidate"] is True
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    selected = report["selected_policy"]
    assert selected["decision"] == "PASS"
    assert selected["metrics"]["target_distribution"]["BUY"] > 0
    assert selected["metrics"]["target_distribution"]["SELL"] > 0


def test_label_horizon_gate_blocks_one_sided_action_policy() -> None:
    df = _synthetic_ohlcv(300, mode="up_only")
    limits = LabelHorizonGateLimits(min_samples=50, min_class_count=5, max_action_side_pct=70.0)
    policies = [LabelPolicyCandidate("test_one_sided", lookahead=5, atr_multiplier=0.5)]
    report = build_label_horizon_recovery(df, policies=policies, limits=limits)
    assert report["decision"] == "BLOCK"
    assert "TARGET_ACTION_SIDE_IMBALANCE_HIGH" in report["reason_codes"] or "TARGET_ACTION_CLASS_COVERAGE_LOW" in report["reason_codes"]
    assert report["approved_for_live_real"] is False


def test_label_horizon_gate_blocks_too_few_samples() -> None:
    df = _synthetic_ohlcv(60)
    report = build_label_horizon_recovery(df, policies=[LabelPolicyCandidate("small", 5, 1.0)])
    assert report["decision"] == "BLOCK"
    assert "LABEL_SAMPLE_COUNT_LOW" in report["reason_codes"]


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    df = _synthetic_ohlcv(300)
    csv_path = tmp_path / "ohlcv.csv"
    out_dir = tmp_path / "reports"
    df.to_csv(csv_path, index=False)
    module = _load_tool_module()
    rc = module.main([
        "--input-csv",
        str(csv_path),
        "--out-dir",
        str(out_dir),
        "--min-samples",
        "50",
        "--max-policies",
        "1",
        "--review-ok",
    ])
    assert rc == 0
    reports = list(out_dir.glob("4B436624H_label_horizon_recovery_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["contract_version"] == LABEL_HORIZON_RECOVERY_CONTRACT_VERSION
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["guardrails"]["post_requests_allowed"] is False

def test_tool_requires_review_ok(tmp_path: Path) -> None:
    df = _synthetic_ohlcv(200)
    csv_path = tmp_path / "ohlcv.csv"
    df.to_csv(csv_path, index=False)
    module = _load_tool_module()
    rc = module.main(["--input-csv", str(csv_path), "--out-dir", str(tmp_path)])
    assert rc == 2
