import pandas as pd

from tradebot.features import build_atr_targets, build_feature_frame, candles_to_frame, latest_feature_row
from tradebot.models import Candle



def _sample_df(rows: int = 80) -> pd.DataFrame:
    return pd.DataFrame({
        'open_time': range(rows),
        'close_time': range(rows),
        'open': [100 + i * 0.1 for i in range(rows)],
        'high': [100.5 + i * 0.1 for i in range(rows)],
        'low': [99.5 + i * 0.1 for i in range(rows)],
        'close': [100 + i * 0.1 for i in range(rows)],
        'volume': [10 + i for i in range(rows)],
        'quote_volume': [1000 + i * 10 for i in range(rows)],
    })



def test_feature_lag_shifts_ema_by_one_bar():
    raw = build_feature_frame(_sample_df(120), feature_lag=0)
    lagged = build_feature_frame(_sample_df(120), feature_lag=1)
    idx = 40
    assert lagged['EMA_9'].iloc[idx] == raw['EMA_9'].iloc[idx - 1]
    assert lagged['close'].iloc[idx] == raw['close'].iloc[idx - 1]



def test_latest_feature_row_ignores_open_candle_noise():
    closed = [
        Candle(open_time=i, close_time=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=10 + i, quote_volume=100 + i, closed=True)
        for i in range(60)
    ]
    noisy_open = Candle(open_time=999, close_time=999, open=1, high=9999, low=1, close=9999, volume=9999, quote_volume=9999, closed=False)
    row_without = latest_feature_row(candles_to_frame(closed))
    row_with = latest_feature_row(candles_to_frame([*closed, noisy_open]))
    assert row_without is not None and row_with is not None
    pd.testing.assert_frame_equal(row_without, row_with)



def test_build_atr_targets_with_feature_lag_produces_clean_numeric_targets():
    labeled = build_atr_targets(_sample_df(140), lookahead=5, atr_multiplier=0.5, feature_lag=1)
    assert not labeled.empty
    assert labeled['target'].dtype.kind in {'i', 'u'}
    assert labeled[['EMA_9', 'EMA_21', 'ATR_14']].dtypes.astype(str).eq('float32').all()
