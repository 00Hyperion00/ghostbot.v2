from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

CLASS_NAME_MAP = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
THRESHOLD_PROFILES = (
    'conservative',
    'balanced',
    'action_seek_light',
)


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    buy_threshold: float
    sell_threshold: float
    hold_band_low: float
    hold_band_high: float
    indecision_margin: float

    def to_dict(self) -> dict[str, float]:
        return {
            'buy_threshold': float(self.buy_threshold),
            'sell_threshold': float(self.sell_threshold),
            'hold_band_low': float(self.hold_band_low),
            'hold_band_high': float(self.hold_band_high),
            'indecision_margin': float(self.indecision_margin),
        }


def get_threshold_config(profile: str = 'balanced') -> ThresholdConfig:
    normalized = str(profile or 'balanced').strip().lower()
    if normalized not in THRESHOLD_PROFILES:
        raise ValueError(f'Unknown threshold profile: {profile}. Expected one of {THRESHOLD_PROFILES}.')
    if normalized == 'conservative':
        return ThresholdConfig(
            buy_threshold=0.72,
            sell_threshold=0.70,
            hold_band_low=0.48,
            hold_band_high=0.60,
            indecision_margin=0.10,
        )
    if normalized == 'action_seek_light':
        return ThresholdConfig(
            buy_threshold=0.58,
            sell_threshold=0.56,
            hold_band_low=0.42,
            hold_band_high=0.52,
            indecision_margin=0.05,
        )
    return ThresholdConfig(
        buy_threshold=0.64,
        sell_threshold=0.62,
        hold_band_low=0.45,
        hold_band_high=0.55,
        indecision_margin=0.08,
    )


def _safe_rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(count) / float(total)


def _class_distribution(values: Iterable[int], labels: list[int]) -> dict[str, int]:
    arr = np.asarray(list(values), dtype=int)
    return {str(label): int(np.sum(arr == label)) for label in labels}


def _class_rate(values: Iterable[int], labels: list[int]) -> dict[str, float]:
    counts = _class_distribution(values, labels)
    total = int(sum(counts.values()))
    return {label: _safe_rate(count, total) for label, count in counts.items()}


def summarize_prediction_distribution(
    y_true: Iterable[int],
    y_pred: Iterable[int],
    proba: Any,
    *,
    labels: list[int] | None = None,
    low_confidence_cutoff: float = 0.55,
    high_confidence_cutoff: float = 0.75,
    indecision_margin_cutoff: float = 0.08,
) -> dict[str, Any]:
    labels = labels or [0, 1, 2]
    y_true_arr = np.asarray(list(y_true), dtype=int)
    y_pred_arr = np.asarray(list(y_pred), dtype=int)
    proba_arr = np.asarray(proba, dtype=float)

    max_probs = proba_arr.max(axis=1)
    sorted_probs = np.sort(proba_arr, axis=1)
    indecision_margin = sorted_probs[:, -1] - sorted_probs[:, -2]
    total = int(len(y_pred_arr))

    predicted_distribution = _class_distribution(y_pred_arr, labels)
    predicted_rate = _class_rate(y_pred_arr, labels)
    actual_distribution = _class_distribution(y_true_arr, labels)
    actual_rate = _class_rate(y_true_arr, labels)

    hold_count = predicted_distribution.get('0', 0)
    non_hold_count = total - hold_count

    def _binary_precision(target: int) -> float:
        predicted_positive = int(np.sum(y_pred_arr == target))
        if predicted_positive == 0:
            return 0.0
        true_positive = int(np.sum((y_true_arr == target) & (y_pred_arr == target)))
        return float(true_positive) / float(predicted_positive)

    def _binary_recall(target: int) -> float:
        actual_positive = int(np.sum(y_true_arr == target))
        if actual_positive == 0:
            return 0.0
        true_positive = int(np.sum((y_true_arr == target) & (y_pred_arr == target)))
        return float(true_positive) / float(actual_positive)

    action_report = {
        'hold_rate': _safe_rate(hold_count, total),
        'non_hold_rate': _safe_rate(non_hold_count, total),
        'action_coverage': _safe_rate(non_hold_count, total),
        'buy_precision': _binary_precision(1),
        'sell_precision': _binary_precision(2),
        'buy_recall': _binary_recall(1),
        'sell_recall': _binary_recall(2),
    }

    confidence_summary = {
        'mean_max_probability': float(np.mean(max_probs)) if total else 0.0,
        'median_max_probability': float(np.median(max_probs)) if total else 0.0,
        'p10_max_probability': float(np.percentile(max_probs, 10)) if total else 0.0,
        'p25_max_probability': float(np.percentile(max_probs, 25)) if total else 0.0,
        'p75_max_probability': float(np.percentile(max_probs, 75)) if total else 0.0,
        'p90_max_probability': float(np.percentile(max_probs, 90)) if total else 0.0,
        'mean_indecision_margin': float(np.mean(indecision_margin)) if total else 0.0,
        'low_confidence_cutoff': float(low_confidence_cutoff),
        'high_confidence_cutoff': float(high_confidence_cutoff),
        'indecision_margin_cutoff': float(indecision_margin_cutoff),
        'low_confidence_rate': _safe_rate(int(np.sum(max_probs < low_confidence_cutoff)), total),
        'high_confidence_rate': _safe_rate(int(np.sum(max_probs >= high_confidence_cutoff)), total),
        'indecision_rate': _safe_rate(int(np.sum(indecision_margin < indecision_margin_cutoff)), total),
    }

    return {
        'actual_class_distribution': actual_distribution,
        'actual_class_rate': actual_rate,
        'predicted_class_distribution': predicted_distribution,
        'predicted_class_rate': predicted_rate,
        'action_report': action_report,
        'confidence_summary': confidence_summary,
        'class_name_map': {str(k): v for k, v in CLASS_NAME_MAP.items() if k in labels},
    }


def calibrate_prediction_decision(
    probs: Iterable[float],
    *,
    raw_pred: int | None = None,
    buy_threshold: float,
    sell_threshold: float,
    hold_band_low: float,
    hold_band_high: float,
    indecision_margin: float,
) -> tuple[int, str]:
    probs_arr = np.asarray(list(probs), dtype=float)
    if probs_arr.ndim != 1 or len(probs_arr) < 3:
        raise ValueError('probs must be a 1D array with at least 3 class columns')

    if raw_pred is None:
        raw_pred = int(np.argmax(probs_arr))
    raw_pred = int(raw_pred)

    if raw_pred == 0:
        return 0, 'RAW_TOP_HOLD'

    hold_p = float(probs_arr[0])
    buy_p = float(probs_arr[1])
    sell_p = float(probs_arr[2])

    action_class = raw_pred
    action_prob = buy_p if action_class == 1 else sell_p
    other_action_prob = sell_p if action_class == 1 else buy_p
    action_threshold = buy_threshold if action_class == 1 else sell_threshold
    action_margin = action_prob - other_action_prob

    # 4B.4.3.5 action-first hotfix:
    # raw BUY/SELL is now preserved by default unless it is materially weak or ambiguous.
    looseness = max(0.0, 0.72 - action_threshold)
    selective_floor = max(0.30, hold_band_low - 0.08, action_threshold - (0.20 + looseness * 0.75))
    acceptance_floor = max(0.34, hold_band_low - 0.03, action_threshold - (0.12 + looseness * 0.80))
    strong_margin_floor = max(0.015, indecision_margin * 0.35)
    soft_margin_floor = max(0.008, indecision_margin * 0.18)
    hold_dominance_limit = max(0.10, indecision_margin * 0.90 + (0.08 - looseness * 0.10))

    if action_prob < selective_floor:
        return 0, 'REJECT_LOW_ACTION_PROB'

    if action_prob >= action_threshold and action_margin >= strong_margin_floor:
        return action_class, 'RAW_ACTION_THRESHOLD_PASS'

    if action_margin < soft_margin_floor:
        return 0, 'REJECT_LOW_MARGIN'

    if hold_p - action_prob > hold_dominance_limit:
        return 0, 'REJECT_HOLD_DOMINANCE'

    if action_prob >= hold_band_high and action_margin >= soft_margin_floor:
        return action_class, 'RAW_ACTION_HIGH_BAND_ACCEPT'

    if action_prob >= acceptance_floor:
        return action_class, 'RAW_ACTION_FIRST_ACCEPT'

    return 0, 'REJECT_FALLBACK_HOLD'


def calibrate_prediction_row(
    probs: Iterable[float],
    *,
    raw_pred: int | None = None,
    buy_threshold: float,
    sell_threshold: float,
    hold_band_low: float,
    hold_band_high: float,
    indecision_margin: float,
) -> int:
    decision, _reason = calibrate_prediction_decision(
        probs,
        raw_pred=raw_pred,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        hold_band_low=hold_band_low,
        hold_band_high=hold_band_high,
        indecision_margin=indecision_margin,
    )
    return decision


def apply_threshold_calibration(
    proba: Any,
    *,
    raw_pred: Iterable[int] | None = None,
    buy_threshold: float,
    sell_threshold: float,
    hold_band_low: float,
    hold_band_high: float,
    indecision_margin: float,
) -> np.ndarray:
    proba_arr = np.asarray(proba, dtype=float)
    if proba_arr.ndim != 2 or proba_arr.shape[1] < 3:
        raise ValueError('proba must be a 2D array with at least 3 class columns')

    if raw_pred is None:
        raw_pred_arr = np.argmax(proba_arr, axis=1)
    else:
        raw_pred_arr = np.asarray(list(raw_pred), dtype=int)
        if len(raw_pred_arr) != len(proba_arr):
            raise ValueError('raw_pred length mismatch')

    decisions = [
        calibrate_prediction_decision(
            probs,
            raw_pred=int(pred),
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            hold_band_low=hold_band_low,
            hold_band_high=hold_band_high,
            indecision_margin=indecision_margin,
        )
        for probs, pred in zip(proba_arr, raw_pred_arr, strict=False)
    ]
    return np.asarray([decision for decision, _reason in decisions], dtype=int)


def summarize_threshold_calibration(
    y_true: Iterable[int],
    proba: Any,
    *,
    raw_pred: Iterable[int] | None = None,
    profile: str = 'balanced',
    labels: list[int] | None = None,
) -> dict[str, Any]:
    config = get_threshold_config(profile)
    raw_pred_arr = np.argmax(np.asarray(proba, dtype=float), axis=1) if raw_pred is None else np.asarray(list(raw_pred), dtype=int)
    decisions = [
        calibrate_prediction_decision(
            probs,
            raw_pred=int(pred),
            buy_threshold=config.buy_threshold,
            sell_threshold=config.sell_threshold,
            hold_band_low=config.hold_band_low,
            hold_band_high=config.hold_band_high,
            indecision_margin=config.indecision_margin,
        )
        for probs, pred in zip(np.asarray(proba, dtype=float), raw_pred_arr, strict=False)
    ]
    calibrated_pred = np.asarray([decision for decision, _reason in decisions], dtype=int)
    reason_counts = dict(sorted(Counter(reason for _decision, reason in decisions).items()))
    distribution = summarize_prediction_distribution(
        y_true,
        calibrated_pred,
        proba,
        labels=labels or [0, 1, 2],
        low_confidence_cutoff=config.hold_band_high,
        high_confidence_cutoff=max(config.buy_threshold, config.sell_threshold),
        indecision_margin_cutoff=config.indecision_margin,
    )
    return {
        'threshold_profile': str(profile),
        'threshold_config': config.to_dict(),
        'calibrated_predictions': calibrated_pred,
        'calibrated_predicted_class_distribution': distribution['predicted_class_distribution'],
        'calibrated_predicted_class_rate': distribution['predicted_class_rate'],
        'calibrated_action_report': distribution['action_report'],
        'calibrated_confidence_summary': distribution['confidence_summary'],
        'calibrated_reason_counts': reason_counts,
    }
