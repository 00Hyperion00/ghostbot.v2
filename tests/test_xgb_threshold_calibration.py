import math

from tradebot.training.calibration import (
    THRESHOLD_PROFILES,
    apply_threshold_calibration,
    calibrate_prediction_decision,
    calibrate_prediction_row,
    get_threshold_config,
    summarize_threshold_calibration,
)


def test_threshold_profiles_are_exposed():
    assert THRESHOLD_PROFILES == ('conservative', 'balanced', 'action_seek_light')


def test_selective_calibration_preserves_raw_hold():
    cfg = get_threshold_config('balanced')
    predicted = calibrate_prediction_row(
        [0.71, 0.20, 0.09],
        raw_pred=0,
        buy_threshold=cfg.buy_threshold,
        sell_threshold=cfg.sell_threshold,
        hold_band_low=cfg.hold_band_low,
        hold_band_high=cfg.hold_band_high,
        indecision_margin=cfg.indecision_margin,
    )
    assert predicted == 0


def test_selective_calibration_keeps_strong_raw_buy():
    cfg = get_threshold_config('balanced')
    predicted = calibrate_prediction_row(
        [0.18, 0.69, 0.13],
        raw_pred=1,
        buy_threshold=cfg.buy_threshold,
        sell_threshold=cfg.sell_threshold,
        hold_band_low=cfg.hold_band_low,
        hold_band_high=cfg.hold_band_high,
        indecision_margin=cfg.indecision_margin,
    )
    assert predicted == 1


def test_apply_threshold_calibration_is_selective_on_raw_non_hold_only():
    cfg = get_threshold_config('balanced')
    proba = [
        [0.74, 0.20, 0.06],
        [0.16, 0.66, 0.18],
        [0.14, 0.18, 0.68],
        [0.52, 0.60, 0.08],
        [0.58, 0.20, 0.22],
    ]
    raw_pred = [0, 1, 2, 1, 0]
    pred = apply_threshold_calibration(
        proba,
        raw_pred=raw_pred,
        buy_threshold=cfg.buy_threshold,
        sell_threshold=cfg.sell_threshold,
        hold_band_low=cfg.hold_band_low,
        hold_band_high=cfg.hold_band_high,
        indecision_margin=cfg.indecision_margin,
    )
    assert pred.tolist() == [0, 1, 2, 1, 0]


def test_profiles_produce_distinct_action_coverage_under_selective_calibration():
    y_true = [0, 1, 2, 1, 2, 0, 1, 2]
    proba = [
        [0.70, 0.18, 0.12],
        [0.25, 0.73, 0.02],
        [0.24, 0.09, 0.71],
        [0.51, 0.60, 0.08],
        [0.50, 0.08, 0.59],
        [0.78, 0.12, 0.10],
        [0.47, 0.58, 0.07],
        [0.46, 0.06, 0.57],
    ]
    raw_pred = [0, 1, 2, 1, 2, 0, 1, 2]

    conservative = summarize_threshold_calibration(y_true, proba, raw_pred=raw_pred, profile='conservative')
    balanced = summarize_threshold_calibration(y_true, proba, raw_pred=raw_pred, profile='balanced')
    light = summarize_threshold_calibration(y_true, proba, raw_pred=raw_pred, profile='action_seek_light')

    assert conservative['calibrated_action_report']['action_coverage'] < light['calibrated_action_report']['action_coverage']
    assert balanced['calibrated_action_report']['action_coverage'] > 0.0
    distributions = {
        tuple(conservative['calibrated_predicted_class_distribution'].values()),
        tuple(balanced['calibrated_predicted_class_distribution'].values()),
        tuple(light['calibrated_predicted_class_distribution'].values()),
    }
    assert len(distributions) >= 2
    assert light['calibrated_predicted_class_distribution']['1'] > 0 or light['calibrated_predicted_class_distribution']['2'] > 0



def test_balanced_profile_rescues_near_threshold_raw_actions_more_than_conservative():
    y_true = [1, 1, 2, 1]
    proba = [
        [0.50, 0.58, 0.07],
        [0.49, 0.57, 0.08],
        [0.46, 0.10, 0.56],
        [0.61, 0.58, 0.04],
    ]
    raw_pred = [1, 1, 2, 1]

    conservative = summarize_threshold_calibration(y_true, proba, raw_pred=raw_pred, profile='conservative')
    balanced = summarize_threshold_calibration(y_true, proba, raw_pred=raw_pred, profile='balanced')
    light = summarize_threshold_calibration(y_true, proba, raw_pred=raw_pred, profile='action_seek_light')

    assert conservative['calibrated_action_report']['action_coverage'] == 0.0
    assert balanced['calibrated_action_report']['action_coverage'] > 0.0
    assert light['calibrated_action_report']['action_coverage'] >= balanced['calibrated_action_report']['action_coverage']


def test_action_first_balanced_accepts_raw_buy_near_threshold():
    cfg = get_threshold_config('balanced')
    predicted, reason = calibrate_prediction_decision(
        [0.39, 0.47, 0.14],
        raw_pred=1,
        buy_threshold=cfg.buy_threshold,
        sell_threshold=cfg.sell_threshold,
        hold_band_low=cfg.hold_band_low,
        hold_band_high=cfg.hold_band_high,
        indecision_margin=cfg.indecision_margin,
    )
    assert predicted == 1
    assert reason in {'RAW_ACTION_FIRST_ACCEPT', 'RAW_ACTION_HIGH_BAND_ACCEPT'}


def test_action_first_conservative_rejects_weaker_raw_buy():
    cfg = get_threshold_config('conservative')
    predicted, reason = calibrate_prediction_decision(
        [0.39, 0.47, 0.14],
        raw_pred=1,
        buy_threshold=cfg.buy_threshold,
        sell_threshold=cfg.sell_threshold,
        hold_band_low=cfg.hold_band_low,
        hold_band_high=cfg.hold_band_high,
        indecision_margin=cfg.indecision_margin,
    )
    assert predicted == 0
    assert reason in {'REJECT_LOW_ACTION_PROB', 'REJECT_FALLBACK_HOLD'}


def test_threshold_summary_exposes_reason_counts():
    y_true = [0, 1, 2, 1]
    proba = [
        [0.70, 0.20, 0.10],
        [0.39, 0.47, 0.14],
        [0.32, 0.18, 0.50],
        [0.44, 0.49, 0.07],
    ]
    raw_pred = [0, 1, 2, 1]
    report = summarize_threshold_calibration(y_true, proba, raw_pred=raw_pred, profile='balanced')
    assert 'calibrated_reason_counts' in report
    assert report['calibrated_reason_counts']
    assert sum(report['calibrated_reason_counts'].values()) == len(y_true)
