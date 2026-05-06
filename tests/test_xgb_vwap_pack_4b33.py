import math

import pandas as pd

from tradebot.features import FEATURE_COLUMNS, build_feature_frame, latest_feature_row


DAY_MS = 86_400_000



def _sample_df() -> pd.DataFrame:
    rows = []
    base_open = 1_700_000_000_000
    for day in range(2):
        for minute in range(60):
            idx = day * 60 + minute
            open_time = base_open + (day * DAY_MS) + (minute * 60_000)
            close_time = open_time + 60_000
            open_price = 100 + (day * 5) + minute * 0.1
            close_price = open_price + (0.2 if minute % 2 == 0 else -0.05)
            high_price = max(open_price, close_price) + 0.3
            low_price = min(open_price, close_price) - 0.2
            volume = 10 + minute
            rows.append({
                'open_time': open_time,
                'close_time': close_time,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'quote_volume': volume * close_price,
            })
    return pd.DataFrame(rows)



def test_vwap_columns_exist_in_feature_schema():
    for column in [
        'vwap_session',
        'close_to_vwap_pct',
        'high_to_vwap_pct',
        'low_to_vwap_pct',
        'vwap_distance_atr_norm',
    ]:
        assert column in FEATURE_COLUMNS



def test_vwap_features_are_numeric():
    featured = build_feature_frame(_sample_df(), feature_lag=0)
    clean = featured.dropna(subset=['vwap_session', 'close_to_vwap_pct', 'high_to_vwap_pct', 'low_to_vwap_pct'])
    assert not clean.empty
    row = clean.iloc[-1]
    assert float(row['vwap_session']) > 0.0
    assert math.isfinite(float(row['close_to_vwap_pct']))
    assert math.isfinite(float(row['high_to_vwap_pct']))
    assert math.isfinite(float(row['low_to_vwap_pct']))



def test_vwap_session_resets_on_new_day():
    featured = build_feature_frame(_sample_df(), feature_lag=0)
    featured = featured.dropna(subset=['vwap_session']).reset_index(drop=True)
    day2_first = featured.iloc[60]
    expected_typical_price = (day2_first['high'] + day2_first['low'] + day2_first['close']) / 3.0
    assert math.isclose(float(day2_first['vwap_session']), float(expected_typical_price), rel_tol=1e-9, abs_tol=1e-9)



def test_vwap_features_obey_feature_lag():
    raw = build_feature_frame(_sample_df(), feature_lag=0)
    lagged = build_feature_frame(_sample_df(), feature_lag=1)
    idx = 80
    assert math.isclose(float(lagged['vwap_session'].iloc[idx]), float(raw['vwap_session'].iloc[idx - 1]), rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(float(lagged['close_to_vwap_pct'].iloc[idx]), float(raw['close_to_vwap_pct'].iloc[idx - 1]), rel_tol=1e-9, abs_tol=1e-9)



def test_latest_feature_row_contains_vwap_pack():
    row = latest_feature_row(_sample_df(), feature_lag=1)
    assert row is not None
    for column in ['vwap_session', 'close_to_vwap_pct', 'high_to_vwap_pct', 'low_to_vwap_pct', 'vwap_distance_atr_norm']:
        assert column in row.columns
        assert str(row[column].dtype) != 'object'
