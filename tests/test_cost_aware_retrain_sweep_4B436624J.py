from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from tradebot.cost_aware_retrain_sweep import (
    COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
    CostAwareRetrainGateLimits,
    build_cost_aware_retrain_sweep_report,
    evaluate_cost_aware_training_result,
    evaluate_sweep_candidate,
    select_best_cost_aware_retrain_candidate,
)


def _load_tool_module():
    script = Path(__file__).resolve().parents[1] / "tools" / "run_cost_aware_retrain_sweep_4B436624J.py"
    spec = importlib.util.spec_from_file_location("run_cost_aware_retrain_sweep_4B436624J", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _passing_training_result() -> dict:
    return {
        "contract_version": COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
        "model_path": "models/candidate.ubj",
        "candidate_spec": {
            "label_policy": {"name": "h30_cost16_edge30_atr3_0"},
            "class_weight_profile": "balanced",
            "threshold_profile": "action_seek_light",
        },
        "label_policy": {"name": "h30_cost16_edge30_atr3_0"},
        "class_weight_profile": "balanced",
        "threshold_profile": "action_seek_light",
        "clean_samples": 5000,
        "accuracy": 0.48,
        "calibrated_accuracy": 0.46,
        "target_distribution": {"0": 4100, "1": 470, "2": 430},
        "validation_actual_class_distribution": {"0": 810, "1": 95, "2": 95},
        "validation_predicted_class_distribution": {"0": 720, "1": 150, "2": 130},
        "calibrated_predicted_class_distribution": {"0": 850, "1": 80, "2": 70},
        "calibrated_reason_counts": {"RAW_ACTION_FIRST_ACCEPT": 150, "REJECT_LOW_MARGIN": 120, "RAW_TOP_HOLD": 730},
        "probability_separation": {
            "buy_sell_margin": {"mean": 0.035, "median": 0.031},
            "action_hold_margin": {"mean": 0.028},
        },
        "synthetic_class_padding_applied": False,
    }


def test_cost_aware_retrain_candidate_gate_can_pass_mock_result() -> None:
    gated = evaluate_sweep_candidate(_passing_training_result())
    assert gated["contract_version"] == COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION
    assert gated["candidate_gate"]["decision"] == "PASS"
    assert gated["approved_for_live_real"] is False
    assert gated["reload_allowed"] is False
    assert gated["score"] > -100


def test_cost_aware_retrain_gate_blocks_weak_probability_separation() -> None:
    result = {
        "clean_samples": 2000,
        "accuracy": 0.45,
        "calibrated_accuracy": 0.45,
        "target_distribution": {"0": 1500, "1": 250, "2": 250},
        "validation_actual_class_distribution": {"0": 100, "1": 50, "2": 50},
        "validation_predicted_class_distribution": {"0": 0, "1": 100, "2": 100},
        "calibrated_predicted_class_distribution": {"0": 200, "1": 0, "2": 0},
        "calibrated_reason_counts": {"REJECT_LOW_MARGIN": 200},
        "probability_separation": {
            "buy_sell_margin": {"mean": 0.001, "median": 0.001},
            "action_hold_margin": {"mean": 0.001},
        },
    }
    gate = evaluate_cost_aware_training_result(result, limits=CostAwareRetrainGateLimits(min_clean_samples=100))
    assert gate["decision"] == "BLOCK"
    assert "BUY_SELL_SEPARATION_MEAN_LOW" in gate["reason_codes"]
    assert "LOW_MARGIN_REJECTION_HIGH" in gate["reason_codes"]
    assert gate["approved_for_live_real"] is False


def test_select_best_prefers_pass_candidate() -> None:
    block = {"decision": "BLOCK", "score": 99.0, "reason_codes": ["X"], "model_path": "bad.ubj"}
    passed = {"decision": "PASS", "score": 1.0, "reason_codes": [], "model_path": "good.ubj"}
    selected = select_best_cost_aware_retrain_candidate([block, passed])
    assert selected["decision"] == "PASS"
    assert selected["approved"] is True
    assert selected["best_candidate"]["model_path"] == "good.ubj"


def test_sweep_report_never_approves_paper_or_live() -> None:
    report = build_cost_aware_retrain_sweep_report([{"decision": "PASS", "score": 1.0, "reason_codes": [], "model_path": "good.ubj"}])
    assert report["decision"] == "PASS"
    assert report["approved_for_training_candidate"] is True
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["guardrails"]["post_requests_allowed"] is False


def test_tool_writes_report_from_candidate_json(tmp_path: Path) -> None:
    candidate_json = tmp_path / "candidate.json"
    out_dir = tmp_path / "reports"
    candidate_json.write_text(json.dumps(_passing_training_result(), ensure_ascii=False), encoding="utf-8")
    module = _load_tool_module()
    rc = module.main([
        "--candidate-json",
        str(candidate_json),
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ])
    assert rc == 0
    reports = list(out_dir.glob("4B436624J_cost_aware_retrain_sweep_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["contract_version"] == COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION
    assert payload["approved_for_training_candidate"] is True
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["guardrails"]["reload_performed"] is False
    assert payload["candidate_count"] == 1


def test_tool_requires_review_ok(tmp_path: Path) -> None:
    candidate_json = tmp_path / "candidate.json"
    candidate_json.write_text(json.dumps(_passing_training_result(), ensure_ascii=False), encoding="utf-8")
    module = _load_tool_module()
    rc = module.main(["--candidate-json", str(candidate_json), "--out-dir", str(tmp_path)])
    assert rc == 2
