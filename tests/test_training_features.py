import pandas as pd

from tradebot.features import FEATURE_COLUMNS, build_atr_targets, build_feature_frame


def _sample_frame(rows: int = 80) -> pd.DataFrame:
    base = [100 + (i * 0.25) + ((-1) ** i) * 0.1 for i in range(rows)]
    return pd.DataFrame({
        'open_time': list(range(rows)),
        'close_time': list(range(rows)),
        'open': [v - 0.05 for v in base],
        'high': [v + 0.2 for v in base],
        'low': [v - 0.2 for v in base],
        'close': base,
        'volume': [1000 + i for i in range(rows)],
    })


def test_build_feature_frame_feature_columns_are_numeric():
    featured = build_feature_frame(_sample_frame())
    dtypes = featured[FEATURE_COLUMNS].dtypes.astype(str).to_dict()
    assert dtypes['RSI_14'] != 'object'
    assert all(dtype != 'object' for dtype in dtypes.values())


def test_build_atr_targets_output_is_trainable_numeric_frame():
    labeled = build_atr_targets(_sample_frame(), lookahead=10, atr_multiplier=1.5)
    X = labeled[FEATURE_COLUMNS].apply(pd.to_numeric, errors='coerce')
    assert not X.empty
    assert X.notna().all(axis=1).all()
