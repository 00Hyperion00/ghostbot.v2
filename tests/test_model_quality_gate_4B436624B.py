from __future__ import annotations

from tradebot.model_quality_gate import (
    ModelQualityGateConfig,
    build_runtime_model_quality_gate,
    evaluate_training_result_quality,
)


def _passing_training_result() -> dict:
    return {
        'clean_samples': 2400,
        'calibrated_accuracy': 0.44,
        'calibrated_action_report': {
            'hold_rate': 0.82,
            'action_coverage': 0.18,
            'non_hold_rate': 0.18,
        },
        'calibrated_reason_counts': {
            'RAW_TOP_HOLD': 1968,
            'RAW_ACTION_FIRST_ACCEPT': 432,
        },
        'calibrated_predicted_class_distribution': {'0': 1968, '1': 216, '2': 216},
    }


def test_training_gate_passes_candidate_with_actionable_coverage() -> None:
    gate = evaluate_training_result_quality(_passing_training_result())

    assert gate['contract_version'] == '4B.4.3.6.6.24B'
    assert gate['decision'] == 'PASS'
    assert gate['reload_allowed'] is True
    assert gate['reason_codes'] == []


def test_training_gate_blocks_hold_dominant_candidate() -> None:
    result = _passing_training_result()
    result['calibrated_action_report'] = {'hold_rate': 0.99, 'action_coverage': 0.01}

    gate = evaluate_training_result_quality(result)

    assert gate['decision'] == 'BLOCK'
    assert gate['reload_allowed'] is False
    assert 'TRAINING_ACTION_COVERAGE_LOW' in gate['reason_codes']
    assert 'TRAINING_HOLD_RATE_TOO_HIGH' in gate['reason_codes']


def test_training_gate_blocks_missing_evidence_by_default() -> None:
    gate = evaluate_training_result_quality({'model_path': 'models/candidate.ubj'})

    assert gate['decision'] == 'BLOCK'
    assert gate['reload_allowed'] is False
    assert 'TRAINING_QUALITY_EVIDENCE_INSUFFICIENT' in gate['reason_codes']
    assert set(gate['metrics']['missing_metrics']) >= {'clean_samples', 'action_coverage', 'hold_rate', 'calibrated_accuracy'}


def test_runtime_gate_blocks_critical_retrain_snapshot() -> None:
    snapshot = {
        'severity': 'critical',
        'recommendation': 'RETRAIN_RECOMMENDED',
        'sample_count': 67,
        'prediction_distribution_pct': {'BUY': 0.0, 'SELL': 0.0, 'HOLD': 100.0},
        'confidence': {'avg': 0.445},
        'calibration': {'reject_low_margin_pct': 80.0},
    }

    gate = build_runtime_model_quality_gate(snapshot)

    assert gate['decision'] == 'BLOCK'
    assert gate['live_demo_allowed'] is False
    assert gate['live_real_allowed'] is False
    assert 'RETRAIN_RECOMMENDED' in gate['reason_codes']
    assert 'RUNTIME_ACTION_COVERAGE_LOW' in gate['reason_codes']


def test_runtime_gate_warns_but_does_not_block_warning_when_configured() -> None:
    snapshot = {
        'severity': 'warning',
        'recommendation': 'MONITOR_OR_RETRAIN',
        'sample_count': 50,
        'prediction_distribution_pct': {'BUY': 6.0, 'SELL': 6.0, 'HOLD': 88.0},
        'confidence': {'avg': 0.51},
        'calibration': {'reject_low_margin_pct': 30.0},
    }

    gate = build_runtime_model_quality_gate(snapshot, config=ModelQualityGateConfig(block_runtime_warning=False))

    assert gate['decision'] == 'WARN'
    assert gate['ok'] is True
    assert gate['live_demo_allowed'] is False
    assert 'MODEL_QUALITY_WARNING' in gate['warnings']
