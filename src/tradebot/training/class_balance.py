from __future__ import annotations

from typing import Iterable, Any

import numpy as np
import pandas as pd

CLASS_WEIGHT_PROFILES = (
    'none',
    'balanced',
    'buy_sell_boost_light',
    'buy_sell_boost_medium',
)


def _normalize_weight_map(weight_map: dict[int, float]) -> dict[int, float]:
    values = np.asarray(list(weight_map.values()), dtype=float)
    mean = float(values.mean()) if len(values) else 1.0
    if mean <= 0:
        return {int(k): 1.0 for k in weight_map}
    return {int(k): float(v) / mean for k, v in weight_map.items()}


def get_class_weight_map(y: Iterable[int], profile: str = 'none', labels: Iterable[int] = (0, 1, 2)) -> dict[int, float]:
    profile = str(profile or 'none').strip().lower()
    labels = [int(label) for label in labels]
    if profile not in CLASS_WEIGHT_PROFILES:
        raise ValueError(f'Unknown class weight profile: {profile}. Expected one of {CLASS_WEIGHT_PROFILES}.')

    if profile == 'none':
        return {label: 1.0 for label in labels}

    y_series = pd.Series(list(y), dtype='int64')
    counts = y_series.value_counts().to_dict()
    total = float(len(y_series)) if len(y_series) else 1.0
    present_labels = max(sum(1 for label in labels if counts.get(label, 0) > 0), 1)

    if profile == 'balanced':
        weights = {}
        for label in labels:
            count = int(counts.get(label, 0))
            weights[label] = float(total / (present_labels * count)) if count > 0 else 1.0
        return _normalize_weight_map(weights)

    base = {label: 1.0 for label in labels}
    if profile == 'buy_sell_boost_light':
        base[0] = 0.90
        base[1] = 1.15
        base[2] = 1.15
    elif profile == 'buy_sell_boost_medium':
        base[0] = 0.80
        base[1] = 1.30
        base[2] = 1.30
    return _normalize_weight_map(base)



def build_sample_weights(y: Iterable[int], profile: str = 'none', labels: Iterable[int] = (0, 1, 2)) -> tuple[np.ndarray, dict[int, float]]:
    y_arr = np.asarray(list(y), dtype=int)
    weight_map = get_class_weight_map(y_arr, profile=profile, labels=labels)
    sample_weights = np.asarray([weight_map.get(int(value), 1.0) for value in y_arr], dtype=float)
    return sample_weights, weight_map



def serialize_class_weight_map(weight_map: dict[int, Any]) -> dict[str, float]:
    return {str(int(key)): float(value) for key, value in weight_map.items()}
