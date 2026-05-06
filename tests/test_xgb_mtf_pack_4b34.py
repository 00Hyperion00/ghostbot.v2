import math

import pandas as pd

from tradebot.features import FEATURE_COLUMNS, build_feature_frame, latest_feature_row


BASE_TS = 1_700_000_000_000


def _sample_df(rows: int = 240) -> pd.DataFrame:
    data = []
    for i in range(rows):
        open_time = BASE_TS + i * 60_000
        close_time = open_time + 60_000
        open_price = 100 + i * 0.05
        close_price = open_price + (0.08 if i % 3 else -0.02)
        high_price = max(open_price, close_price) + 0.12
        low_price = min(open_price, close_price) - 0.07
        volume = 10 + (i % 20)
        data.append({
            'open_time': open_time,
            'close_time': close_time,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'quote_volume': volume * close_price,
        })
    return pd.DataFrame(data)


def test_mtf_columns_exist_in_feature_schema():
    for column in [
        'mtf_15m_trend_flag',
        'mtf_15m_ema_gap_pct',
        'mtf_15m_rsi_14',
        'mtf_15m_close_to_ema21_pct',
    ]:
        assert column in FEATURE_COLUMNS



def test_mtf_features_are_numeric():
    featured = build_feature_frame(_sample_df(), feature_lag=0)
    clean = featured.dropna(subset=['mtf_15m_trend_flag', 'mtf_15m_ema_gap_pct', 'mtf_15m_rsi_14', 'mtf_15m_close_to_ema21_pct'])
    assert not clean.empty
    row = clean.iloc[-1]
    assert float(row['mtf_15m_trend_flag']) in {-1.0, 0.0, 1.0}
    assert math.isfinite(float(row['mtf_15m_ema_gap_pct']))
    assert 0.0 <= float(row['mtf_15m_rsi_14']) <= 100.0
    assert math.isfinite(float(row['mtf_15m_close_to_ema21_pct']))



def test_mtf_features_obey_feature_lag():
    raw = build_feature_frame(_sample_df(), feature_lag=0)
    lagged = build_feature_frame(_sample_df(), feature_lag=1)
    idx = 180
    assert math.isclose(float(lagged['mtf_15m_ema_gap_pct'].iloc[idx]), float(raw['mtf_15m_ema_gap_pct'].iloc[idx - 1]), rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(float(lagged['mtf_15m_close_to_ema21_pct'].iloc[idx]), float(raw['mtf_15m_close_to_ema21_pct'].iloc[idx - 1]), rel_tol=1e-9, abs_tol=1e-9)
    assert float(lagged['mtf_15m_trend_flag'].iloc[idx]) == float(raw['mtf_15m_trend_flag'].iloc[idx - 1])



def test_latest_feature_row_contains_mtf_pack():
    row = latest_feature_row(_sample_df(), feature_lag=1)
    assert row is not None
    for column in ['mtf_15m_trend_flag', 'mtf_15m_ema_gap_pct', 'mtf_15m_rsi_14', 'mtf_15m_close_to_ema21_pct']:
        assert column in row.columns
        assert str(row[column].dtype) != 'object'
