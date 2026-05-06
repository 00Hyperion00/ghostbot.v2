from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from tradebot.runtime_calibration_probe import (
    RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION,
    ThresholdProfile,
    build_runtime_calibration_probe,
    build_threshold_sweep,
    calibrate_probabilities,
    extract_runtime_probability_sample,
)


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "run_runtime_calibration_probe_4B436624E.py"
    spec = importlib.util.spec_from_file_location("run_runtime_calibration_probe_4B436624E", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def status_payload(*, hold: float, buy: float, sell: float, signal: str = "HOLD", reason: str = "REJECT_LOW_MARGIN") -> dict[str, Any]:
    probs = [hold, buy, sell]
    raw_class = max(range(3), key=lambda idx: probs[idx])
    return {
        "symbol": "ETHUSDT",
        "last_signal": signal,
        "last_evaluated_close_time": 123456789,
        "ai_snapshot": {
            "model_path": "models/ETHUSDT_model_4b436624D.ubj",
            "metrics": {
                "holdProbability": hold,
                "buyProbability": buy,
                "sellProbability": sell,
                "rawPredictedClass": raw_class,
                "calibratedClass": {"HOLD": 0, "BUY": 1, "SELL": 2}[signal],
                "calibrationReason": reason,
                "rawTopProbability": probs[raw_class],
                "rawMargin": abs(buy - sell),
            },
        },
        "decision_audit_snapshot": {
            "threshold_trace": {
                "buy_threshold": 0.64,
                "sell_threshold": 0.57,
                "hold_band_low": 0.45,
                "hold_band_high": 0.55,
                "indecision_margin": 0.08,
            }
        },
    }


def test_calibration_probe_extracts_runtime_probabilities() -> None:
    sample = extract_runtime_probability_sample(status_payload(hold=0.10, buy=0.44, sell=0.46), sample_index=7)
    assert sample is not None
    assert sample["contract_version"] == RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION
    assert sample["sample_index"] == 7
    assert sample["raw_signal"] == "SELL"
    assert sample["calibrated_signal"] == "HOLD"
    assert sample["calibration_reason"] == "REJECT_LOW_MARGIN"


def test_threshold_sweep_identifies_calibration_suppression() -> None:
    statuses = [status_payload(hold=0.10, buy=0.44, sell=0.46) for _ in range(35)]
    samples = [extract_runtime_probability_sample(status, sample_index=i) for i, status in enumerate(statuses)]
    report = build_runtime_calibration_probe([sample for sample in samples if sample is not None], min_samples=30)

    assert report["decision"] == "BLOCK"
    assert report["conclusion"] == "CALIBRATION_SUPPRESSION"
    assert report["metrics"]["raw_action_pct"] == 100.0
    assert report["metrics"]["current_action_pct"] == 0.0
    assert report["metrics"]["relaxed_best_action_pct"] == 100.0
    assert "RELAXED_THRESHOLDS_INCREASE_ACTION_COVERAGE" in report["warnings"]


def test_raw_model_collapse_is_not_treated_as_threshold_problem() -> None:
    statuses = [status_payload(hold=0.54, buy=0.23, sell=0.23, reason="RAW_TOP_HOLD") for _ in range(32)]
    samples = [extract_runtime_probability_sample(status, sample_index=i) for i, status in enumerate(statuses)]
    report = build_runtime_calibration_probe([sample for sample in samples if sample is not None], min_samples=30)

    assert report["conclusion"] == "RAW_MODEL_COLLAPSE"
    assert report["metrics"]["raw_action_pct"] == 0.0
    assert report["metrics"]["relaxed_best_action_pct"] == 0.0
    assert "RAW_ACTION_COVERAGE_ZERO" in report["reason_codes"]


def test_calibrate_probabilities_matches_runtime_low_margin_rule() -> None:
    strict = ThresholdProfile(name="strict", indecision_margin=0.08)
    loose = ThresholdProfile(name="loose", indecision_margin=0.0, hold_band_low=0.35, sell_threshold=0.45)

    strict_result = calibrate_probabilities(0.10, 0.44, 0.46, strict)
    loose_result = calibrate_probabilities(0.10, 0.44, 0.46, loose)

    assert strict_result["calibrated_signal"] == "HOLD"
    assert strict_result["calibration_reason"] == "REJECT_LOW_MARGIN"
    assert loose_result["calibrated_signal"] == "SELL"


def test_probe_tool_is_get_only_and_writes_reports(tmp_path: Path) -> None:
    tool = load_tool()
    calls: list[str] = []
    statuses = [status_payload(hold=0.10, buy=0.44, sell=0.46) for _ in range(3)]

    def fetcher(base_url: str, path: str, timeout_sec: float) -> dict[str, Any]:
        calls.append(path)
        assert path == "/status"
        return statuses[min(len(calls) - 1, len(statuses) - 1)]

    report = tool.run_probe(
        base_url="http://127.0.0.1:8000",
        duration_sec=0,
        interval_sec=1,
        timeout_sec=1,
        max_samples=3,
        min_samples=1,
        fetcher=fetcher,
    )
    paths = tool.write_reports(tmp_path, report)

    assert calls == ["/status", "/status", "/status"]
    assert report["observation_only"] is True
    assert report["no_post_actions"] is True
    assert report["guardrails"]["post_requests_allowed"] is False
    assert Path(paths["report_json"]).exists()
    assert Path(paths["sweep_json"]).exists()
    saved = json.loads(Path(paths["report_json"]).read_text(encoding="utf-8"))
    assert saved["contract_version"] == RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION


def test_input_json_loader_accepts_status_list(tmp_path: Path) -> None:
    tool = load_tool()
    input_path = tmp_path / "statuses.json"
    input_path.write_text(json.dumps([status_payload(hold=0.10, buy=0.44, sell=0.46)]), encoding="utf-8")

    report = tool.run_probe(input_json=str(input_path), min_samples=1)

    assert report["sample_count"] == 1
    assert report["status_count"] == 1
    assert report["metrics"]["raw_action_pct"] == 100.0


def test_source_contract_has_no_post_method() -> None:
    source = (Path(__file__).resolve().parents[1] / "tools" / "run_runtime_calibration_probe_4B436624E.py").read_text(encoding="utf-8")
    assert "method=\"GET\"" in source
    assert "method=\"POST\"" not in source
    assert "post_requests_allowed" in source
