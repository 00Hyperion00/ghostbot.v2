from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from tradebot.probability_separation_gate import (
    PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION,
    build_label_calibration_report,
    build_probability_separation_gate,
    extract_probability_samples_from_payload,
)
from tools import run_probability_separation_recovery_4B436624G as tool


def _sample(*, buy: float, sell: float, hold: float, current: str = "HOLD", reason: str = "REJECT_LOW_MARGIN", idx: int = 0):
    raw_signal = "BUY" if buy >= sell and buy >= hold else ("SELL" if sell >= hold else "HOLD")
    raw_class = {"HOLD": 0, "BUY": 1, "SELL": 2}[raw_signal]
    return {
        "sample_index": idx,
        "hold_probability": hold,
        "buy_probability": buy,
        "sell_probability": sell,
        "raw_predicted_class": raw_class,
        "raw_signal": raw_signal,
        "calibrated_signal": current,
        "current_signal": current,
        "calibration_reason": reason,
        "raw_margin": abs(buy - sell),
    }


def test_separation_gate_blocks_tight_buy_sell_probability_gap() -> None:
    samples = [_sample(buy=0.455, sell=0.451, hold=0.094, idx=i) for i in range(41)]

    report = build_probability_separation_gate(samples)

    assert report["contract_version"] == PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION
    assert report["decision"] == "BLOCK"
    assert "BUY_SELL_SEPARATION_MEAN_LOW" in report["reason_codes"]
    assert "BUY_SELL_SEPARATION_MEDIAN_LOW" in report["reason_codes"]
    assert "LOW_MARGIN_REJECTION_HIGH" in report["reason_codes"]
    assert report["approved_for_live_real"] is False


def test_separation_gate_passes_healthy_probability_separation() -> None:
    samples = []
    for i in range(8):
        samples.append(_sample(buy=0.72, sell=0.12, hold=0.16, current="BUY", reason="RAW_ACTION_FIRST_ACCEPT", idx=i))
    for i in range(8, 16):
        samples.append(_sample(buy=0.14, sell=0.70, hold=0.16, current="SELL", reason="RAW_ACTION_FIRST_ACCEPT", idx=i))
    for i in range(16, 40):
        samples.append(_sample(buy=0.33, sell=0.32, hold=0.34, current="HOLD", reason="RAW_TOP_HOLD", idx=i))

    report = build_probability_separation_gate(samples)

    assert report["decision"] == "PASS"
    assert report["approved_for_paper_candidate"] is True
    assert report["approved_for_live_real"] is False
    assert report["metrics"]["buy_sell_margin"]["mean"] > 0.015


def test_extracts_samples_from_24e_probe_report_shape() -> None:
    payload = {
        "report_type": "runtime_calibration_probe",
        "samples": [
            _sample(buy=0.46, sell=0.45, hold=0.09, idx=0),
            _sample(buy=0.12, sell=0.68, hold=0.20, current="SELL", reason="RAW_ACTION_FIRST_ACCEPT", idx=1),
        ],
    }

    samples, rejected = extract_probability_samples_from_payload(payload)

    assert len(samples) == 2
    assert rejected == []
    assert samples[0]["buy_probability"] == 0.46


def test_label_calibration_report_flags_side_imbalance() -> None:
    training = {
        "target_distribution": {"0": 800, "1": 190, "2": 10},
        "validation_predicted_class_distribution": {"0": 500, "1": 450, "2": 50},
        "calibrated_predicted_class_distribution": {"0": 750, "1": 230, "2": 20},
        "synthetic_class_padding_applied": False,
    }

    report = build_label_calibration_report(training)

    assert report["decision"] == "WARN"
    assert "LABEL_SIDE_IMBALANCE_ELEVATED" in report["warnings"]
    assert report["metrics"]["target_action_rate"] == 0.2


def test_tool_writes_report_from_input_json(tmp_path: Path) -> None:
    input_path = tmp_path / "probe.json"
    samples = []
    for i in range(35):
        samples.append(_sample(buy=0.455, sell=0.451, hold=0.094, idx=i))
    input_path.write_text(json.dumps({"samples": samples}), encoding="utf-8")
    args = Namespace(
        input_json=str(input_path),
        training_json=None,
        base_url="http://127.0.0.1:8000",
        duration_min=0.0,
        interval_sec=60.0,
        timeout_sec=5.0,
        max_samples=100,
        min_samples=30,
        out_dir=str(tmp_path / "reports"),
        min_buy_sell_margin_mean=0.015,
        min_buy_sell_margin_median=0.010,
        min_action_hold_margin_mean=0.060,
        max_raw_action_pct=85.0,
        min_raw_action_pct=2.0,
        max_action_side_pct=80.0,
        min_directional_entropy=0.55,
        max_low_margin_reject_pct=60.0,
        max_current_action_pct=45.0,
        min_current_action_pct_for_ready=2.0,
    )

    report = tool.run(args)

    assert report["decision"] == "BLOCK"
    assert Path(report["report_json"]).exists()
    assert Path(report["report_md"]).exists()
    saved = json.loads(Path(report["report_json"]).read_text(encoding="utf-8"))
    assert saved["guardrails"]["post_requests_allowed"] is False
