import math

import pandas as pd

from tradebot.features import FEATURE_COLUMNS, build_feature_frame, latest_feature_row


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        'open_time': range(80),
        'close_time': range(80),
        'open': [100 + i * 0.1 for i in range(80)],
        'high': [100.6 + i * 0.1 for i in range(80)],
        'low': [99.8 + i * 0.1 for i in range(80)],
        'close': [100.3 + i * 0.1 for i in range(80)],
        'volume': [10 + i for i in range(80)],
        'quote_volume': [1000 + i * 10 for i in range(80)],
    })


def test_price_action_columns_exist_in_feature_schema():
    assert 'body_pct' in FEATURE_COLUMNS
    assert 'upper_wick_pct' in FEATURE_COLUMNS
    assert 'lower_wick_pct' in FEATURE_COLUMNS
    assert 'close_location_pct' in FEATURE_COLUMNS
    assert 'range_atr_ratio' in FEATURE_COLUMNS
    assert 'bullish_engulfing_flag' in FEATURE_COLUMNS
    assert 'bearish_engulfing_flag' in FEATURE_COLUMNS


def test_price_action_features_are_numeric_and_bounded():
    featured = build_feature_frame(_sample_df(), feature_lag=0)
    clean = featured.dropna(subset=['body_pct', 'upper_wick_pct', 'lower_wick_pct', 'close_location_pct', 'range_atr_ratio'])
    assert not clean.empty
    row = clean.iloc[-1]
    assert 0.0 <= float(row['body_pct']) <= 1.0
    assert 0.0 <= float(row['upper_wick_pct']) <= 1.0
    assert 0.0 <= float(row['lower_wick_pct']) <= 1.0
    assert 0.0 <= float(row['close_location_pct']) <= 1.0
    assert float(row['range_atr_ratio']) >= 0.0
    total = float(row['body_pct'] + row['upper_wick_pct'] + row['lower_wick_pct'])
    assert math.isclose(total, 1.0, rel_tol=1e-5, abs_tol=1e-5)


def test_bullish_engulfing_flag_detects_pattern():
    rows = []
    for i in range(60):
        rows.append({
            'open_time': i, 'close_time': i, 'open': 100 + i * 0.1, 'high': 100.5 + i * 0.1,
            'low': 99.7 + i * 0.1, 'close': 100.2 + i * 0.1, 'volume': 10 + i, 'quote_volume': 1000 + i,
        })
    rows[-2].update({'open': 110.0, 'high': 110.2, 'low': 108.7, 'close': 109.0})
    rows[-1].update({'open': 108.8, 'high': 110.8, 'low': 108.5, 'close': 110.5})
    df = pd.DataFrame(rows)
    featured = build_feature_frame(df, feature_lag=0)
    assert int(featured['bullish_engulfing_flag'].iloc[-1]) == 1
    assert int(featured['bearish_engulfing_flag'].iloc[-1]) == 0


def test_price_action_features_obey_feature_lag():
    raw = build_feature_frame(_sample_df(), feature_lag=0)
    lagged = build_feature_frame(_sample_df(), feature_lag=1)
    idx = 40
    assert lagged['body_pct'].iloc[idx] == raw['body_pct'].iloc[idx - 1]
    assert lagged['close_location_pct'].iloc[idx] == raw['close_location_pct'].iloc[idx - 1]


def test_latest_feature_row_contains_price_action_pack():
    row = latest_feature_row(_sample_df(), feature_lag=1)
    assert row is not None
    for column in ['body_pct', 'upper_wick_pct', 'lower_wick_pct', 'close_location_pct', 'range_atr_ratio']:
        assert column in row.columns
        assert str(row[column].dtype) != 'object'
