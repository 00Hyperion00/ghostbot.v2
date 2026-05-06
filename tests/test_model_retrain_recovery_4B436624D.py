from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from tradebot.model_quality_gate import evaluate_training_result_quality
from tradebot.training.retrain_recovery import (
    RETRAIN_RECOVERY_CONTRACT_VERSION,
    build_candidate_matrix,
    build_dataset_quality_report,
    evaluate_retrain_candidate,
    select_best_retrain_candidate,
)
from tools import run_model_retrain_recovery_4B436624D as recovery_tool


def _candidate_result(**overrides):
    payload = {
        "model_path": "models/candidate.ubj",
        "clean_samples": 2400,
        "calibrated_accuracy": 0.44,
        "calibrated_action_report": {"hold_rate": 0.82, "action_coverage": 0.18, "non_hold_rate": 0.18},
        "calibrated_reason_counts": {"RAW_TOP_HOLD": 1968, "RAW_ACTION_FIRST_ACCEPT": 432},
        "calibrated_predicted_class_distribution": {"0": 1968, "1": 216, "2": 216},
        "target_distribution": {"0": 1900, "1": 260, "2": 240},
        "synthetic_class_padding_applied": False,
    }
    payload.update(overrides)
    return payload


def test_train_gate_blocks_synthetic_class_padding() -> None:
    gate = evaluate_training_result_quality(_candidate_result(synthetic_class_padding_applied=True))

    assert gate["decision"] == "BLOCK"
    assert gate["reload_allowed"] is False
    assert "TRAINING_SYNTHETIC_CLASS_PADDING_USED" in gate["reason_codes"]


def test_dataset_quality_blocks_target_hold_collapse() -> None:
    report = build_dataset_quality_report(_candidate_result(target_distribution={"0": 2400, "1": 0, "2": 0}))

    assert report["contract_version"] == RETRAIN_RECOVERY_CONTRACT_VERSION
    assert report["decision"] == "BLOCK"
    assert "TARGET_ACTION_RATE_LOW" in report["reason_codes"]
    assert "TARGET_ACTION_CLASS_MISSING" in report["reason_codes"]


def test_retrain_candidate_passes_when_training_and_dataset_quality_pass() -> None:
    report = evaluate_retrain_candidate(_candidate_result(), candidate_spec={"days": 60})

    assert report["decision"] == "PASS"
    assert report["reload_allowed"] is True
    assert report["candidate_spec"]["days"] == 60


def test_select_best_candidate_requires_pass() -> None:
    weak = evaluate_retrain_candidate(_candidate_result(calibrated_action_report={"hold_rate": 0.995, "action_coverage": 0.005}))
    strong = evaluate_retrain_candidate(_candidate_result(calibrated_accuracy=0.47))

    selected = select_best_retrain_candidate([weak, strong])

    assert selected["decision"] == "PASS"
    assert selected["approved"] is True
    assert selected["best_candidate"]["decision"] == "PASS"


def test_candidate_matrix_expands_days_profiles_and_thresholds() -> None:
    specs = build_candidate_matrix(
        days=[30, 60],
        class_weight_profiles=["balanced", "buy_sell_boost_light"],
        threshold_profiles=["balanced", "action_seek_light"],
        feature_lag=1,
        max_candidates=5,
    )

    assert len(specs) == 5
    assert specs[0].days == 30
    assert "balanced" in specs[0].slug()


def test_recovery_tool_dry_run_writes_reports(tmp_path: Path) -> None:
    args = Namespace(
        symbol="ETHUSDT",
        interval="1m",
        base_url="https://example.invalid",
        days="30,60",
        class_weight_profiles="balanced",
        threshold_profiles="balanced,action_seek_light",
        feature_lag=1,
        max_candidates=3,
        out_dir=str(tmp_path / "models"),
        reports_dir=str(tmp_path / "reports"),
        dry_run=True,
        stop_on_error=False,
        promote=False,
        promote_to=str(tmp_path / "models" / "approved.ubj"),
        min_clean_samples=1000,
        min_action_coverage=0.03,
        max_hold_rate=0.97,
        max_low_margin_reject_rate=0.75,
        min_calibrated_accuracy=0.30,
        min_target_action_rate=0.03,
        max_target_hold_rate=0.97,
        min_present_target_classes=2,
    )

    payload = recovery_tool.run(args)

    assert payload["contract_version"] == RETRAIN_RECOVERY_CONTRACT_VERSION
    assert payload["decision"] == "PLAN"
    assert payload["candidate_count"] == 3
    assert Path(payload["report_json"]).exists()
    saved = json.loads(Path(payload["report_json"]).read_text(encoding="utf-8"))
    assert saved["guardrails"]["reload_performed"] is False

