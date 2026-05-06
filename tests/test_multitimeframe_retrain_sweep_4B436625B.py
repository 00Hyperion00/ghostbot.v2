from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.multitimeframe_retrain_sweep_25b import (
    MultiTimeframeRetrainGateLimits,
    build_mtf_15m_retrain_sweep,
    evaluate_mtf_retrain_candidate_result,
    parse_policy_name,
    policies_from_25a_report,
)


def _passing_candidate() -> dict:
    return {
        "model_path": "models/mock.ubj",
        "candidate_spec": {"policy": {"name": "mtf_15m_h16_cost20_edge40_atr3_0"}, "class_weight_profile": "balanced", "threshold_profile": "paper_guarded"},
        "metrics": {
            "clean_samples": 5000,
            "target_action_pct": 17.5,
            "target_hold_pct": 82.5,
            "target_action_side_pct": 51.0,
            "validation_raw_action_pct": 24.0,
            "validation_calibrated_action_pct": 13.0,
            "validation_calibrated_action_side_pct": 54.0,
            "buy_sell_margin_mean": 0.052,
            "buy_sell_margin_median": 0.031,
            "action_hold_margin_mean": 0.024,
            "accuracy": 0.48,
            "calibrated_accuracy": 0.72,
            "action_precision": 0.41,
            "expected_edge_proxy_bps": 18.0,
        },
    }


def test_parse_policy_name_extracts_15m_policy() -> None:
    policy = parse_policy_name("mtf_15m_h16_cost20_edge40_atr3_0")
    assert policy.interval == "15m"
    assert policy.lookahead == 16
    assert policy.cost_bps == 20.0
    assert policy.min_edge_bps == 40.0
    assert policy.atr_multiplier == 3.0


def test_policies_from_25a_report_prefers_selected_15m() -> None:
    report = {"selected_policy": "mtf_15m_h8_cost16_edge30_atr2_5"}
    policies = policies_from_25a_report(report)
    assert policies[0].name == "mtf_15m_h8_cost16_edge30_atr2_5"


def test_mtf_retrain_candidate_gate_can_pass_mock_result() -> None:
    gate = evaluate_mtf_retrain_candidate_result(_passing_candidate())
    assert gate.decision == "PASS"
    assert gate.approved_for_training_candidate is True
    assert gate.approved_for_paper_candidate is False
    assert gate.approved_for_live_real is False
    assert gate.reload_allowed is False


def test_mtf_retrain_candidate_gate_blocks_negative_edge() -> None:
    candidate = _passing_candidate()
    candidate["metrics"]["expected_edge_proxy_bps"] = -4.0
    gate = evaluate_mtf_retrain_candidate_result(candidate)
    assert gate.decision == "BLOCK"
    assert "MTF_RETRAIN_EXPECTED_EDGE_PROXY_LOW" in gate.reason_codes


def test_sweep_report_selects_best_pass_candidate() -> None:
    good = _passing_candidate()
    good_gate = evaluate_mtf_retrain_candidate_result(good)
    good.update({"candidate_gate": good_gate.__dict__, "decision": good_gate.decision, "ok": good_gate.ok, "score": good_gate.score, "reason_codes": good_gate.reason_codes, "warnings": good_gate.warnings})
    bad = _passing_candidate()
    bad["metrics"]["expected_edge_proxy_bps"] = -20.0
    bad_gate = evaluate_mtf_retrain_candidate_result(bad)
    bad.update({"candidate_gate": bad_gate.__dict__, "decision": bad_gate.decision, "ok": bad_gate.ok, "score": bad_gate.score, "reason_codes": bad_gate.reason_codes, "warnings": bad_gate.warnings})
    report = build_mtf_15m_retrain_sweep([bad, good], source="unit")
    assert report["decision"] == "PASS"
    assert report["approved_for_training_candidate"] is True
    assert report["approved_for_live_real"] is False


def test_tool_writes_report_from_candidate_json(tmp_path: Path) -> None:
    candidate = _passing_candidate()
    gate = evaluate_mtf_retrain_candidate_result(candidate)
    candidate.update({"candidate_gate": gate.__dict__, "decision": gate.decision, "ok": gate.ok, "score": gate.score, "reason_codes": gate.reason_codes, "warnings": gate.warnings})
    candidate_path = tmp_path / "candidate.json"
    out_dir = tmp_path / "reports"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "run_multitimeframe_retrain_sweep_4B436625B.py"),
        "--candidate-json",
        str(candidate_path),
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "15m multi-timeframe retrain sweep PASS" in result.stdout
    assert list(out_dir.glob("4B436625B_15m_mtf_retrain_sweep_*.json"))
