from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pandas as pd

from tradebot.cost_aware_label_policy_recovery import (
    COST_AWARE_LABEL_POLICY_CONTRACT_VERSION,
    CostAwareLabelPolicyCandidate,
    CostAwareLabelPolicyGateLimits,
    build_cost_aware_label_policy_recovery,
)


def _synthetic_ohlcv(rows: int = 1800, *, mode: str = "waves") -> pd.DataFrame:
    close = []
    price = 100.0
    for i in range(rows):
        if mode == "noise":
            step = 0.002 * math.sin(i / 3.0)
        elif mode == "up_only":
            step = 0.11 + 0.01 * math.sin(i / 9.0)
        else:
            wave = math.sin(i / 22.0)
            step = 0.18 * (1.0 if wave >= 0 else -1.0) + 0.02 * math.sin(i / 5.0)
        price = max(10.0, price + step)
        close.append(price)
    out = pd.DataFrame({"close": close})
    out["open"] = out["close"].shift(1).fillna(out["close"])
    spread = 0.08 if mode != "noise" else 0.01
    out["high"] = out[["open", "close"]].max(axis=1) + spread
    out["low"] = out[["open", "close"]].min(axis=1) - spread
    out["volume"] = 100 + (pd.Series(range(rows)) % 20) * 4
    out["quote_volume"] = out["volume"] * out["close"]
    out["open_time"] = pd.Series(range(rows), dtype="int64") * 60_000
    out["close_time"] = out["open_time"] + 59_999
    return out[["open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"]]


def _load_tool_module():
    script = Path(__file__).resolve().parents[1] / "tools" / "run_cost_aware_label_policy_recovery_4B436624I.py"
    spec = importlib.util.spec_from_file_location("run_cost_aware_label_policy_recovery_4B436624I", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cost_aware_gate_passes_directional_policy() -> None:
    df = _synthetic_ohlcv(450)
    limits = CostAwareLabelPolicyGateLimits(
        min_samples=80,
        min_action_pct=2.0,
        max_action_pct=100.0,
        min_hold_pct=0.0,
        max_hold_pct=98.0,
        max_action_side_pct=90.0,
        min_directional_entropy=0.35,
        min_forward_return_gap_bps=1.0,
        min_buy_direction_consistency_pct=45.0,
        min_sell_direction_consistency_pct=45.0,
        min_expected_net_edge_bps=-20.0,
        min_class_count=5,
        min_effective_min_profit_bps=1.0,
    )
    policies = [CostAwareLabelPolicyCandidate("test_cost_edge", lookahead=5, atr_multiplier=0.6, cost_bps=2.0, min_edge_bps=2.0)]
    report = build_cost_aware_label_policy_recovery(df, policies=policies, limits=limits)
    assert report["contract_version"] == COST_AWARE_LABEL_POLICY_CONTRACT_VERSION
    assert report["decision"] == "PASS"
    assert report["approved_for_training_candidate"] is True
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    selected = report["selected_policy"]
    assert selected["decision"] == "PASS"
    assert selected["metrics"]["effective_min_profit_bps"] >= 4.0
    assert selected["metrics"]["target_distribution"]["BUY"] > 0
    assert selected["metrics"]["target_distribution"]["SELL"] > 0


def test_cost_aware_gate_blocks_micro_noise_policy() -> None:
    df = _synthetic_ohlcv(450, mode="noise")
    limits = CostAwareLabelPolicyGateLimits(min_samples=80, min_class_count=5, min_expected_net_edge_bps=1.0, min_effective_min_profit_bps=12.0)
    policies = [CostAwareLabelPolicyCandidate("noise_policy", lookahead=5, atr_multiplier=0.4, cost_bps=8.0, min_edge_bps=10.0)]
    report = build_cost_aware_label_policy_recovery(df, policies=policies, limits=limits)
    assert report["decision"] == "BLOCK"
    assert report["approved_for_live_real"] is False
    assert any(code in report["reason_codes"] for code in ["TARGET_ACTION_COVERAGE_LOW", "TARGET_ACTION_CLASS_COVERAGE_LOW", "EXPECTED_NET_EDGE_LOW", "FORWARD_RETURN_SEPARATION_LOW"])


def test_cost_aware_gate_blocks_no_cost_diagnostic_policy() -> None:
    df = _synthetic_ohlcv(450)
    limits = CostAwareLabelPolicyGateLimits(min_samples=80, min_effective_min_profit_bps=12.0)
    policies = [CostAwareLabelPolicyCandidate("diagnostic_zero_cost", 5, 0.6, cost_bps=0.0, min_edge_bps=0.0, approvable=False)]
    report = build_cost_aware_label_policy_recovery(df, policies=policies, limits=limits)
    assert report["decision"] == "BLOCK"
    assert "DIAGNOSTIC_POLICY_NOT_APPROVABLE" in report["reason_codes"]
    assert "EFFECTIVE_MIN_PROFIT_BELOW_COST_FLOOR" in report["reason_codes"]


def test_tool_writes_report_from_input_csv(tmp_path: Path) -> None:
    df = _synthetic_ohlcv(450)
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
        "80",
        "--max-policies",
        "2",
        "--review-ok",
    ])
    assert rc == 0
    reports = list(out_dir.glob("4B436624I_cost_aware_label_policy_recovery_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["contract_version"] == COST_AWARE_LABEL_POLICY_CONTRACT_VERSION
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["guardrails"]["post_requests_allowed"] is False
    assert payload["guardrails"]["config_mutation_performed"] is False


def test_tool_requires_review_ok(tmp_path: Path) -> None:
    df = _synthetic_ohlcv(200)
    csv_path = tmp_path / "ohlcv.csv"
    df.to_csv(csv_path, index=False)
    module = _load_tool_module()
    rc = module.main(["--input-csv", str(csv_path), "--out-dir", str(tmp_path)])
    assert rc == 2
