from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from tradebot.calibration_policy_gate import CALIBRATION_POLICY_GATE_CONTRACT_VERSION, CalibrationPolicyGateLimits, build_calibration_policy_gate, evaluate_calibration_profile
from tradebot.runtime_calibration_probe import ThresholdProfile, extract_runtime_probability_sample


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "run_calibration_policy_gate_4B436624F.py"
    spec = importlib.util.spec_from_file_location("run_calibration_policy_gate_4B436624F", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def status_payload(*, hold: float, buy: float, sell: float, signal: str = "HOLD") -> dict[str, Any]:
    probs = [hold, buy, sell]
    raw_class = max(range(3), key=lambda idx: probs[idx])
    return {"symbol": "ETHUSDT", "last_signal": signal, "ai_snapshot": {"model_path": "models/ETHUSDT_model_4b436624D.ubj", "metrics": {"holdProbability": hold, "buyProbability": buy, "sellProbability": sell, "rawPredictedClass": raw_class, "calibratedClass": 0, "calibrationReason": "REJECT_LOW_MARGIN", "rawTopProbability": probs[raw_class], "rawMargin": abs(buy - sell)}}, "decision_audit_snapshot": {"threshold_trace": {"buy_threshold": 0.64, "sell_threshold": 0.57, "hold_band_low": 0.45, "hold_band_high": 0.55, "indecision_margin": 0.08}}}


def balanced_samples() -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for _ in range(12):
        statuses.append(status_payload(hold=0.09, buy=0.456, sell=0.450))
    for _ in range(12):
        statuses.append(status_payload(hold=0.09, buy=0.450, sell=0.456))
    for _ in range(16):
        statuses.append(status_payload(hold=0.09, buy=0.452, sell=0.450))
    samples = [extract_runtime_probability_sample(status, sample_index=i) for i, status in enumerate(statuses)]
    return [sample for sample in samples if sample is not None]


def test_policy_gate_selects_paper_candidate_without_live_real_approval() -> None:
    report = build_calibration_policy_gate(balanced_samples(), limits=CalibrationPolicyGateLimits(min_samples=30, max_action_pct=70.0, max_action_side_pct=85.0))
    assert report["contract_version"] == CALIBRATION_POLICY_GATE_CONTRACT_VERSION
    assert report["decision"] == "PASS"
    assert report["approved_for_paper_candidate"] is True
    assert report["approved_for_live_real"] is False
    assert report["live_real_allowed"] is False
    assert report["guardrails"]["post_requests_allowed"] is False
    assert report["selected_profile"]["profile"]["name"] != "no_margin_probe"


def test_no_margin_profile_is_never_approvable() -> None:
    profile = ThresholdProfile(name="no_margin_probe", buy_threshold=0.45, sell_threshold=0.45, hold_band_low=0.35, hold_band_high=0.65, indecision_margin=0.0)
    result = evaluate_calibration_profile(balanced_samples(), profile, limits=CalibrationPolicyGateLimits(min_samples=30, max_action_pct=100.0), approvable=False)
    assert result["decision"] == "BLOCK"
    assert "DIAGNOSTIC_PROFILE_NOT_APPROVABLE" in result["reason_codes"]
    assert "ZERO_MARGIN_PROFILE_NOT_APPROVABLE" in result["reason_codes"]


def test_gate_blocks_excessive_action_coverage() -> None:
    profile = ThresholdProfile(name="too_loose", buy_threshold=0.45, sell_threshold=0.45, hold_band_low=0.35, hold_band_high=0.65, indecision_margin=0.002)
    result = evaluate_calibration_profile(balanced_samples(), profile, limits=CalibrationPolicyGateLimits(min_samples=30, max_action_pct=10.0), approvable=True)
    assert result["decision"] == "BLOCK"
    assert "CALIBRATED_ACTION_COVERAGE_TOO_HIGH" in result["reason_codes"]


def test_gate_blocks_one_sided_action_distribution() -> None:
    statuses = [status_payload(hold=0.09, buy=0.456, sell=0.450) for _ in range(35)]
    samples = [extract_runtime_probability_sample(status, sample_index=i) for i, status in enumerate(statuses)]
    report = build_calibration_policy_gate([sample for sample in samples if sample is not None], limits=CalibrationPolicyGateLimits(min_samples=30, max_action_pct=100.0, max_action_side_pct=85.0))
    assert report["decision"] == "BLOCK"
    assert any("ACTION_SIDE_IMBALANCE_HIGH" in item["reason_codes"] for item in report["profiles"] if item["approvable"])


def test_tool_reads_24e_report_samples_and_writes_report(tmp_path: Path) -> None:
    tool = load_tool()
    input_path = tmp_path / "24e_report.json"
    input_path.write_text(json.dumps({"samples": balanced_samples()}), encoding="utf-8")
    report = tool.run_gate(input_json=str(input_path), min_samples=30, max_action_pct=70.0)
    paths = tool.write_report(tmp_path, report)
    assert report["sample_count"] == 40
    assert report["decision"] == "PASS"
    assert Path(paths["report_json"]).exists()
    assert Path(paths["report_md"]).exists()


def test_tool_is_get_only_when_collecting_status() -> None:
    tool = load_tool()
    calls: list[str] = []
    statuses = [status_payload(hold=0.09, buy=0.456, sell=0.450) for _ in range(3)]
    def fetcher(base_url: str, path: str, timeout_sec: float) -> dict[str, Any]:
        calls.append(path)
        assert path == "/status"
        return statuses[min(len(calls) - 1, len(statuses) - 1)]
    report = tool.run_gate(duration_sec=3, interval_sec=0.1, max_samples=3, min_samples=1, max_action_pct=100.0, fetcher=fetcher)
    assert calls == ["/status", "/status", "/status"]
    assert report["no_post_actions"] is True
    assert report["config_mutation_performed"] is False
    assert report["guardrails"]["post_requests_allowed"] is False


def test_source_contract_has_no_post_method() -> None:
    source = (Path(__file__).resolve().parents[1] / "tools" / "run_calibration_policy_gate_4B436624F.py").read_text(encoding="utf-8")
    assert "method=\"GET\"" in source
    assert "method=\"POST\"" not in source
    assert "post_requests_allowed" in source
