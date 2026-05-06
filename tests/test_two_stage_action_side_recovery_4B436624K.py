from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.cost_aware_label_policy_recovery import default_cost_aware_label_policy_candidates
from tradebot.two_stage_action_side_recovery import (
    TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
    TwoStageActionSideCandidateSpec,
    build_two_stage_candidate_specs,
    build_two_stage_recovery_report,
    evaluate_two_stage_training_result,
)


def _policy():
    return next(p for p in default_cost_aware_label_policy_candidates() if p.name == "h30_cost16_edge30_atr3_0")


def test_two_stage_candidate_gate_can_pass_mock_result() -> None:
    result = {
        "clean_samples": 5000,
        "target_distribution": {"HOLD": 4100, "BUY": 460, "SELL": 440},
        "validation_staged_distribution": {"HOLD": 880, "BUY": 65, "SELL": 55},
        "metrics": {
            "target_action_pct": 18.0,
            "target_hold_pct": 82.0,
            "target_action_side_pct": 51.1,
            "target_directional_entropy": 0.99,
            "validation_staged_action_pct": 12.0,
            "validation_staged_action_side_pct": 54.2,
            "validation_action_precision": 0.18,
            "validation_action_recall": 0.16,
            "validation_action_f1": 0.17,
            "validation_side_accuracy": 0.56,
            "validation_side_precision_sell": 0.18,
            "action_probability_gap_mean": 0.035,
            "action_auc_proxy_gap": 0.025,
            "expected_edge_proxy_bps": 4.0,
        },
    }
    gate = evaluate_two_stage_training_result(result)
    assert gate["contract_version"] == TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION
    assert gate["decision"] == "PASS"
    assert gate["approved_for_training_candidate"] is True
    assert gate["approved_for_live_real"] is False


def test_two_stage_candidate_gate_blocks_weak_action_hold_gap() -> None:
    result = {
        "clean_samples": 5000,
        "target_distribution": {"HOLD": 4100, "BUY": 460, "SELL": 440},
        "validation_staged_distribution": {"HOLD": 995, "BUY": 3, "SELL": 2},
        "metrics": {
            "target_action_pct": 18.0,
            "target_hold_pct": 82.0,
            "target_action_side_pct": 51.1,
            "target_directional_entropy": 0.99,
            "validation_staged_action_pct": 0.5,
            "validation_staged_action_side_pct": 60.0,
            "validation_action_precision": 0.05,
            "validation_action_recall": 0.02,
            "validation_action_f1": 0.03,
            "validation_side_accuracy": 0.50,
            "validation_side_precision_sell": 0.04,
            "action_probability_gap_mean": -0.01,
            "action_auc_proxy_gap": -0.01,
            "expected_edge_proxy_bps": -2.0,
        },
    }
    gate = evaluate_two_stage_training_result(result)
    assert gate["decision"] == "BLOCK"
    assert "ACTION_HOLD_PROBABILITY_GAP_LOW" in gate["reason_codes"]
    assert "TWO_STAGE_STAGED_ACTION_COVERAGE_LOW" in gate["reason_codes"]


def test_build_two_stage_candidate_specs_limits_count() -> None:
    specs = build_two_stage_candidate_specs([_policy()], max_candidates=3)
    assert len(specs) == 3
    assert all(isinstance(spec, TwoStageActionSideCandidateSpec) for spec in specs)
    assert specs[0].slug().startswith("h30_cost16_edge30_atr3_0")


def test_build_two_stage_recovery_report_selects_best_pass() -> None:
    weak = {
        "action_model_path": "models/a.ubj",
        "side_model_path": "models/s.ubj",
        "clean_samples": 5000,
        "target_distribution": {"HOLD": 4100, "BUY": 460, "SELL": 440},
        "validation_staged_distribution": {"HOLD": 1000, "BUY": 0, "SELL": 0},
        "metrics": {"validation_staged_action_pct": 0.0, "validation_action_precision": 0.0},
    }
    strong = {
        "action_model_path": "models/a2.ubj",
        "side_model_path": "models/s2.ubj",
        "clean_samples": 5000,
        "target_distribution": {"HOLD": 4100, "BUY": 460, "SELL": 440},
        "validation_staged_distribution": {"HOLD": 880, "BUY": 65, "SELL": 55},
        "metrics": {
            "target_action_pct": 18.0,
            "target_hold_pct": 82.0,
            "target_action_side_pct": 51.1,
            "target_directional_entropy": 0.99,
            "validation_staged_action_pct": 12.0,
            "validation_staged_action_side_pct": 54.2,
            "validation_action_precision": 0.18,
            "validation_action_recall": 0.16,
            "validation_action_f1": 0.17,
            "validation_side_accuracy": 0.56,
            "validation_side_precision_sell": 0.18,
            "action_probability_gap_mean": 0.035,
            "action_auc_proxy_gap": 0.025,
            "expected_edge_proxy_bps": 4.0,
        },
    }
    report = build_two_stage_recovery_report([weak, strong], source="unit")
    assert report["decision"] == "PASS"
    assert report["approved_for_training_candidate"] is True
    assert report["approved_for_paper_candidate"] is False
    assert report["selection"]["best_candidate"]["action_model_path"] == "models/a2.ubj"


def test_tool_writes_report_from_candidate_json(tmp_path: Path) -> None:
    candidate = {
        "action_model_path": "models/action.ubj",
        "side_model_path": "models/side.ubj",
        "clean_samples": 5000,
        "target_distribution": {"HOLD": 4100, "BUY": 460, "SELL": 440},
        "validation_staged_distribution": {"HOLD": 880, "BUY": 65, "SELL": 55},
        "metrics": {
            "target_action_pct": 18.0,
            "target_hold_pct": 82.0,
            "target_action_side_pct": 51.1,
            "target_directional_entropy": 0.99,
            "validation_staged_action_pct": 12.0,
            "validation_staged_action_side_pct": 54.2,
            "validation_action_precision": 0.18,
            "validation_action_recall": 0.16,
            "validation_action_f1": 0.17,
            "validation_side_accuracy": 0.56,
            "validation_side_precision_sell": 0.18,
            "action_probability_gap_mean": 0.035,
            "action_auc_proxy_gap": 0.025,
            "expected_edge_proxy_bps": 4.0,
        },
    }
    candidate_json = tmp_path / "candidates.json"
    candidate_json.write_text(json.dumps({"candidates": [candidate]}), encoding="utf-8")
    out_dir = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_two_stage_action_side_recovery_4B436624K.py",
            "--candidate-json",
            str(candidate_json),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "two-stage action/side recovery PASS" in result.stdout
    reports = list(out_dir.glob("4B436624K_two_stage_action_side_recovery_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["decision"] == "PASS"
    assert payload["approved_for_live_real"] is False
