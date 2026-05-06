from pathlib import Path

import pandas as pd

from tradebot.features import FEATURE_COLUMNS, build_atr_targets, latest_feature_row
from tradebot.training.train_xgb import _ensure_training_matrix
from tradebot.training.calibration import summarize_prediction_distribution


def _sample_df(rows: int = 80) -> pd.DataFrame:
    return pd.DataFrame({
        'open_time': range(rows),
        'close_time': range(rows),
        'open': [100 + i * 0.1 for i in range(rows)],
        'high': [100.5 + i * 0.1 for i in range(rows)],
        'low': [99.5 + i * 0.1 for i in range(rows)],
        'close': [100 + i * 0.1 for i in range(rows)],
        'volume': [10 + i for i in range(rows)],
    })


def test_latest_feature_row_is_numeric():
    row = latest_feature_row(_sample_df())
    assert row is not None
    assert list(row.columns) == FEATURE_COLUMNS
    assert all(str(dtype) != 'object' for dtype in row.dtypes)


def test_training_matrix_cleans_object_columns():
    labeled = build_atr_targets(_sample_df(120), lookahead=5, atr_multiplier=0.5)
    labeled['RSI_14'] = labeled['RSI_14'].astype('object')
    X, y = _ensure_training_matrix(labeled)
    assert not X.empty
    assert not y.empty
    assert str(X['RSI_14'].dtype) != 'object'


def test_prediction_distribution_summary_is_json_friendly():
    report = summarize_prediction_distribution(
        [0, 1, 2, 0],
        [0, 1, 0, 2],
        [
            [0.8, 0.1, 0.1],
            [0.2, 0.7, 0.1],
            [0.4, 0.3, 0.3],
            [0.2, 0.2, 0.6],
        ],
    )
    assert report['predicted_class_distribution']['0'] == 2
    assert 'confidence_summary' in report


def test_class_balance_profile_is_recorded_in_train_result(tmp_path, monkeypatch):
    import pandas as pd
    from tradebot.training import train_xgb as train_mod

    def fake_fetch(symbol, interval, days, base_url='https://api.binance.com'):
        rows = 180
        return pd.DataFrame({
            'open_time': range(rows),
            'close_time': range(rows),
            'open': [100 + ((i % 9) - 4) * 0.35 + i * 0.01 for i in range(rows)],
            'high': [101 + ((i % 11) - 5) * 0.40 + i * 0.01 for i in range(rows)],
            'low': [99 + ((i % 7) - 3) * 0.40 + i * 0.01 for i in range(rows)],
            'close': [100 + ((i % 13) - 6) * 0.45 + i * 0.01 for i in range(rows)],
            'volume': [10 + i for i in range(rows)],
            'quote_volume': [1000 + i * 3 for i in range(rows)],
        })

    monkeypatch.setattr(train_mod, 'fetch_klines', fake_fetch)
    result = train_mod.train('ETHUSDT', '1m', 1, str(tmp_path / 'model.ubj'), class_weight_profile='buy_sell_boost_light')
    assert result['class_weight_profile'] == 'buy_sell_boost_light'
    assert result['class_weight_map']['1'] > result['class_weight_map']['0']


def test_threshold_profile_is_recorded_in_train_result(tmp_path, monkeypatch):
    import pandas as pd
    from tradebot.training import train_xgb as train_mod

    def fake_fetch(symbol, interval, days, base_url='https://api.binance.com'):
        rows = 180
        return pd.DataFrame({
            'open_time': range(rows),
            'close_time': range(rows),
            'open': [100 + ((i % 9) - 4) * 0.35 + i * 0.01 for i in range(rows)],
            'high': [101 + ((i % 11) - 5) * 0.40 + i * 0.01 for i in range(rows)],
            'low': [99 + ((i % 7) - 3) * 0.40 + i * 0.01 for i in range(rows)],
            'close': [100 + ((i % 13) - 6) * 0.45 + i * 0.01 for i in range(rows)],
            'volume': [10 + i for i in range(rows)],
            'quote_volume': [1000 + i * 3 for i in range(rows)],
        })

    monkeypatch.setattr(train_mod, 'fetch_klines', fake_fetch)
    result = train_mod.train('ETHUSDT', '1m', 1, str(tmp_path / 'model.ubj'), class_weight_profile='buy_sell_boost_light', threshold_profile='action_seek_light')
    assert result['threshold_profile'] == 'action_seek_light'
    assert result['threshold_config']['buy_threshold'] == 0.58
    assert 'calibrated_action_report' in result
