from pathlib import Path

import pandas as pd

from tradebot.ai.provider import XGBoostSignalProvider
from tradebot.features import FEATURE_COLUMNS


def test_provider_reports_missing_model(tmp_path: Path):
    provider = XGBoostSignalProvider(str(tmp_path / 'missing_model.ubj'))
    assert not provider.available
    error_text = (provider._load_error or '').lower()
    assert 'no such file' in error_text or 'cannot open' in error_text or 'model' in error_text or 'cannot find the file specified' in error_text


def test_provider_emits_buy_when_raw_buy_confidence_is_strong(monkeypatch):
    provider = XGBoostSignalProvider.__new__(XGBoostSignalProvider)
    provider.model_path = 'dummy'
    provider.threshold = 0.60
    provider._model = type('M', (), {'predict_proba': lambda self, row: [[0.18, 0.71, 0.11]]})()
    provider._load_error = None
    provider.buy_threshold = 0.64
    provider.sell_threshold = 0.57
    provider.hold_band_low = 0.45
    provider.hold_band_high = 0.55
    provider.indecision_margin = 0.08
    provider._resolved_model_path = 'dummy.ubj'
    provider._feature_schema = type('S', (), {'version': '4B.3.4'})()
    provider._feature_lag = 1
    provider._schema_validated = True

    monkeypatch.setattr(
        'tradebot.ai.provider.candles_to_frame',
        lambda candles, closed_only=True: pd.DataFrame([{
            'open_time': 1, 'close_time': 2, 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5, 'volume': 10.0,
        }] * 40),
    )
    monkeypatch.setattr(
        'tradebot.ai.provider.latest_feature_row',
        lambda df, feature_lag=1: pd.DataFrame([{c: 1.0 for c in FEATURE_COLUMNS}]),
    )
    decision = XGBoostSignalProvider.predict(provider, [{'closeTime': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10}], symbol='ETHUSDT', interval='1m')
    assert decision.signal == 'BUY'


def test_provider_holds_when_raw_signal_is_hold(monkeypatch):
    provider = XGBoostSignalProvider.__new__(XGBoostSignalProvider)
    provider.model_path = 'dummy'
    provider.threshold = 0.60
    provider._model = type('M', (), {'predict_proba': lambda self, row: [[0.72, 0.18, 0.10]]})()
    provider._load_error = None
    provider.buy_threshold = 0.64
    provider.sell_threshold = 0.57
    provider.hold_band_low = 0.45
    provider.hold_band_high = 0.55
    provider.indecision_margin = 0.08
    provider._resolved_model_path = 'dummy.ubj'
    provider._feature_schema = type('S', (), {'version': '4B.3.4'})()
    provider._feature_lag = 1
    provider._schema_validated = True

    monkeypatch.setattr(
        'tradebot.ai.provider.candles_to_frame',
        lambda candles, closed_only=True: pd.DataFrame([{
            'open_time': 1, 'close_time': 2, 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5, 'volume': 10.0,
        }] * 40),
    )
    monkeypatch.setattr(
        'tradebot.ai.provider.latest_feature_row',
        lambda df, feature_lag=1: pd.DataFrame([{c: 1.0 for c in FEATURE_COLUMNS}]),
    )
    decision = XGBoostSignalProvider.predict(provider, [{'closeTime': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10}], symbol='ETHUSDT', interval='1m')
    assert decision.signal == 'HOLD'


def test_provider_allows_action_first_buy_below_legacy_global_threshold(monkeypatch):
    provider = XGBoostSignalProvider.__new__(XGBoostSignalProvider)
    provider.model_path = 'dummy'
    provider.threshold = 0.60
    provider._model = type('M', (), {'predict_proba': lambda self, row: [[0.39, 0.47, 0.14]]})()
    provider._load_error = None
    provider.buy_threshold = 0.64
    provider.sell_threshold = 0.57
    provider.hold_band_low = 0.45
    provider.hold_band_high = 0.55
    provider.indecision_margin = 0.08
    provider._resolved_model_path = 'dummy.ubj'
    provider._feature_schema = type('S', (), {'version': '4B.3.4'})()
    provider._feature_lag = 1
    provider._schema_validated = True

    monkeypatch.setattr(
        'tradebot.ai.provider.candles_to_frame',
        lambda candles, closed_only=True: pd.DataFrame([{
            'open_time': 1, 'close_time': 2, 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5, 'volume': 10.0,
        }] * 40),
    )
    monkeypatch.setattr(
        'tradebot.ai.provider.latest_feature_row',
        lambda df, feature_lag=1: pd.DataFrame([{c: 1.0 for c in FEATURE_COLUMNS}]),
    )
    decision = XGBoostSignalProvider.predict(provider, [{'closeTime': 1, 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10}], symbol='ETHUSDT', interval='1m')
    assert decision.signal == 'BUY'
    assert decision.metrics['calibrationReason'] in {'RAW_ACTION_FIRST_ACCEPT', 'RAW_ACTION_HIGH_BAND_ACCEPT'}
