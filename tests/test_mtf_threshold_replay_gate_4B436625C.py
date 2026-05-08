from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.mtf_threshold_replay_gate_25c import (
    ThresholdReplayProfile,
    build_threshold_replay_gate,
    evaluate_samples_with_profiles,
    evaluate_threshold_replay_profile,
    samples_from_json,
)


def test_threshold_replay_profile_can_pass_positive_edge_samples() -> None:
    probs = []
    actual = []
    edges = []
    for i in range(900):
        if i % 10 == 0:
            probs.append([0.31, 0.61, 0.08])
            actual.append(1)
            edges.append(42.0)
        elif i % 10 == 1:
            probs.append([0.32, 0.07, 0.61])
            actual.append(2)
            edges.append(40.0)
        else:
            probs.append([0.66, 0.18, 0.16])
            actual.append(0)
            edges.append(0.0)
    ev = evaluate_threshold_replay_profile(
        probs,
        actual,
        edges,
        ThresholdReplayProfile("paper_guarded_test", 0.55, 0.55, 0.40, 0.56, 0.02),
    )
    assert ev.decision == "PASS"
    assert ev.approved_for_training_candidate is True
    assert ev.approved_for_live_real is False
    assert ev.metrics["expected_edge_proxy_bps"] > 0


def test_threshold_replay_blocks_low_action_coverage() -> None:
    probs = [[0.80, 0.10, 0.10] for _ in range(800)]
    actual = [0 for _ in probs]
    edges = [0.0 for _ in probs]
    ev = evaluate_threshold_replay_profile(
        probs,
        actual,
        edges,
        ThresholdReplayProfile("strict", 0.70, 0.70, 0.45, 0.55, 0.04),
    )
    assert ev.decision == "BLOCK"
    assert "MTF_THRESHOLD_REPLAY_ACTION_COVERAGE_LOW" in ev.reason_codes


def test_diagnostic_zero_margin_profile_not_approvable() -> None:
    probs = [[0.20, 0.55, 0.25] for _ in range(800)]
    actual = [1 for _ in probs]
    edges = [30.0 for _ in probs]
    ev = evaluate_threshold_replay_profile(
        probs,
        actual,
        edges,
        ThresholdReplayProfile("micro_action_probe", 0.45, 0.45, 0.35, 0.65, 0.0, approvable=False),
    )
    assert ev.decision == "BLOCK"
    assert "DIAGNOSTIC_THRESHOLD_PROFILE_NOT_APPROVABLE" in ev.reason_codes
    assert "INDECISION_MARGIN_BELOW_FLOOR" in ev.reason_codes


def test_build_threshold_replay_gate_selects_pass() -> None:
    probs = []
    actual = []
    edges = []
    for i in range(1000):
        if i % 12 == 0:
            probs.append([0.33, 0.60, 0.07]); actual.append(1); edges.append(35.0)
        elif i % 12 == 1:
            probs.append([0.33, 0.07, 0.60]); actual.append(2); edges.append(35.0)
        else:
            probs.append([0.68, 0.17, 0.15]); actual.append(0); edges.append(0.0)
    evals = evaluate_samples_with_profiles(probs, actual, edges, ["balanced", "paper_guarded"])
    report = build_threshold_replay_gate(evals, source="unit")
    assert report["decision"] == "PASS"
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False


def test_samples_from_json_parses_probability_samples() -> None:
    payload = {
        "samples": [
            {"probabilities": [0.2, 0.6, 0.2], "actual": "BUY", "edge_bps": 30},
            {"holdProbability": 0.7, "buyProbability": 0.2, "sellProbability": 0.1, "actual": 0, "edge_bps": 0},
        ]
    }
    probs, actual, edges = samples_from_json(payload)
    assert probs == [[0.2, 0.6, 0.2], [0.7, 0.2, 0.1]]
    assert actual == [1, 0]
    assert edges == [30.0, 0.0]


def test_tool_writes_report_from_sample_json(tmp_path: Path) -> None:
    samples = []
    for i in range(900):
        if i % 10 == 0:
            samples.append({"probabilities": [0.32, 0.60, 0.08], "actual": "BUY", "edge_bps": 36})
        elif i % 10 == 1:
            samples.append({"probabilities": [0.32, 0.08, 0.60], "actual": "SELL", "edge_bps": 36})
        else:
            samples.append({"probabilities": [0.69, 0.16, 0.15], "actual": "HOLD", "edge_bps": 0})
    sample_path = tmp_path / "samples.json"
    sample_path.write_text(json.dumps({"samples": samples}), encoding="utf-8")
    out_dir = tmp_path / "reports"
    cmd = [
        sys.executable,
        "tools/run_15m_threshold_replay_gate_4B436625C.py",
        "--sample-json",
        str(sample_path),
        "--threshold-profiles",
        "paper_guarded",
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "25C 15m threshold/calibration replay gate PASS" in result.stdout
    assert list(out_dir.glob("4B436625C_15m_threshold_replay_gate_*.json"))
