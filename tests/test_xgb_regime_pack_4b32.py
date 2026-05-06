import math

import pandas as pd

from tradebot.features import FEATURE_COLUMNS, build_feature_frame, latest_feature_row


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        'open_time': range(120),
        'close_time': range(120),
        'open': [100 + i * 0.15 for i in range(120)],
        'high': [100.8 + i * 0.18 for i in range(120)],
        'low': [99.7 + i * 0.12 for i in range(120)],
        'close': [100.25 + i * 0.16 for i in range(120)],
        'volume': [10 + i for i in range(120)],
        'quote_volume': [1000 + i * 12 for i in range(120)],
    })


def test_regime_columns_exist_in_feature_schema():
    for column in [
        'bb_width',
        'atr_pct',
        'ema_spread_pct',
        'trend_strength_proxy',
        'volatility_regime_flag',
        'range_regime_flag',
    ]:
        assert column in FEATURE_COLUMNS


def test_regime_features_are_numeric_and_non_negative():
    featured = build_feature_frame(_sample_df(), feature_lag=0)
    clean = featured.dropna(subset=['bb_width', 'atr_pct', 'ema_spread_pct', 'trend_strength_proxy'])
    assert not clean.empty
    row = clean.iloc[-1]
    assert float(row['bb_width']) >= 0.0
    assert float(row['atr_pct']) >= 0.0
    assert float(row['ema_spread_pct']) >= 0.0
    assert float(row['trend_strength_proxy']) >= 0.0
    assert float(row['volatility_regime_flag']) in {0.0, 1.0}
    assert float(row['range_regime_flag']) in {0.0, 1.0}


def test_regime_features_obey_feature_lag():
    raw = build_feature_frame(_sample_df(), feature_lag=0)
    lagged = build_feature_frame(_sample_df(), feature_lag=1)
    idx = 60
    assert math.isclose(float(lagged['bb_width'].iloc[idx]), float(raw['bb_width'].iloc[idx - 1]), rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(float(lagged['atr_pct'].iloc[idx]), float(raw['atr_pct'].iloc[idx - 1]), rel_tol=1e-9, abs_tol=1e-9)
    assert float(lagged['volatility_regime_flag'].iloc[idx]) == float(raw['volatility_regime_flag'].iloc[idx - 1])


def test_latest_feature_row_contains_regime_pack():
    row = latest_feature_row(_sample_df(), feature_lag=1)
    assert row is not None
    for column in ['bb_width', 'atr_pct', 'ema_spread_pct', 'trend_strength_proxy', 'volatility_regime_flag', 'range_regime_flag']:
        assert column in row.columns
        assert str(row[column].dtype) != 'object'
