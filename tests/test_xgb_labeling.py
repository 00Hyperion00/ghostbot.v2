import pandas as pd

from tradebot.training.labeling import ATRLabelConfig, build_cost_aware_atr_targets


def _flat_move_df() -> pd.DataFrame:
    rows = 80
    close = [100.0] * rows
    return pd.DataFrame({
        'open_time': range(rows),
        'close_time': range(rows),
        'open': close,
        'high': [100.1] * rows,
        'low': [99.9] * rows,
        'close': close,
        'volume': [10 + i for i in range(rows)],
        'quote_volume': [1000 + i * 5 for i in range(rows)],
    })


def _first_hit_df() -> pd.DataFrame:
    rows = 80
    close = [100.0] * rows
    high = [100.2] * rows
    low = [99.8] * rows
    # first actionable window after warmup should hit upper barrier first, then lower.
    high[35] = 101.6
    low[36] = 98.0
    return pd.DataFrame({
        'open_time': range(rows),
        'close_time': range(rows),
        'open': close,
        'high': high,
        'low': low,
        'close': close,
        'volume': [10 + i for i in range(rows)],
        'quote_volume': [1000 + i * 5 for i in range(rows)],
    })


def test_cost_aware_labeling_holds_when_move_does_not_clear_cost_floor():
    config = ATRLabelConfig(lookahead=5, atr_multiplier=0.1, min_profit_bps=50.0)
    labeled = build_cost_aware_atr_targets(_flat_move_df(), config=config, feature_lag=1)
    assert not labeled.empty
    assert set(labeled['target'].unique().tolist()) == {0}
    assert labeled.attrs['label_config']['round_trip_cost_bps'] > 0


def test_cost_aware_labeling_uses_first_barrier_hit_order():
    config = ATRLabelConfig(lookahead=5, atr_multiplier=0.5, min_profit_bps=0.0)
    labeled = build_cost_aware_atr_targets(_first_hit_df(), config=config, feature_lag=1)
    assert not labeled.empty
    assert 1 in labeled['target'].tolist()
