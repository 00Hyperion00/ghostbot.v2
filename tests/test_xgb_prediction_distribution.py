import math

from tradebot.training.calibration import summarize_prediction_distribution


def test_prediction_distribution_report_has_expected_keys():
    y_true = [0, 1, 2, 0, 1, 2]
    y_pred = [0, 1, 0, 0, 2, 2]
    proba = [
        [0.90, 0.05, 0.05],
        [0.10, 0.80, 0.10],
        [0.45, 0.30, 0.25],
        [0.70, 0.20, 0.10],
        [0.20, 0.39, 0.41],
        [0.15, 0.15, 0.70],
    ]

    report = summarize_prediction_distribution(y_true, y_pred, proba)

    assert report['actual_class_distribution'] == {'0': 2, '1': 2, '2': 2}
    assert report['predicted_class_distribution'] == {'0': 3, '1': 1, '2': 2}
    assert math.isclose(report['predicted_class_rate']['0'], 0.5)
    assert math.isclose(report['action_report']['hold_rate'], 0.5)
    assert math.isclose(report['action_report']['action_coverage'], 0.5)
    assert 0.0 <= report['confidence_summary']['low_confidence_rate'] <= 1.0
    assert 0.0 <= report['confidence_summary']['indecision_rate'] <= 1.0
    assert report['class_name_map']['0'] == 'HOLD'


def test_prediction_distribution_report_flags_low_confidence_and_indecision():
    y_true = [0, 1, 2]
    y_pred = [0, 1, 2]
    proba = [
        [0.34, 0.33, 0.33],
        [0.20, 0.56, 0.24],
        [0.10, 0.12, 0.78],
    ]

    report = summarize_prediction_distribution(
        y_true,
        y_pred,
        proba,
        low_confidence_cutoff=0.60,
        high_confidence_cutoff=0.75,
        indecision_margin_cutoff=0.05,
    )

    assert math.isclose(report['confidence_summary']['low_confidence_rate'], 2 / 3, rel_tol=1e-9)
    assert math.isclose(report['confidence_summary']['high_confidence_rate'], 1 / 3, rel_tol=1e-9)
    assert math.isclose(report['confidence_summary']['indecision_rate'], 1 / 3, rel_tol=1e-9)
