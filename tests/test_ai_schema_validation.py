from __future__ import annotations

from pathlib import Path

import pytest

from tradebot.ai.provider import XGBoostSignalProvider
from tradebot.features import FEATURE_COLUMNS, get_default_feature_schema
from tradebot.training.feature_schema import FeatureSchema, write_feature_schema


class _FakeBooster:
    feature_names = list(FEATURE_COLUMNS)


class _FakeModel:
    def get_booster(self):
        return _FakeBooster()


def _provider() -> XGBoostSignalProvider:
    provider = object.__new__(XGBoostSignalProvider)
    provider.model_path = 'dummy.ubj'
    provider.threshold = 0.60
    provider.buy_threshold = 0.64
    provider.sell_threshold = 0.57
    provider.hold_band_low = 0.45
    provider.hold_band_high = 0.55
    provider.indecision_margin = 0.08
    provider._model = None
    provider._load_error = None
    provider._feature_schema = None
    provider._schema_path = None
    provider._schema_validated = False
    provider._feature_lag = 1
    provider._resolved_model_path = None
    return provider


def test_provider_rejects_missing_schema_sidecar(tmp_path: Path):
    model_path = tmp_path / 'model.ubj'
    provider = _provider()

    with pytest.raises(FileNotFoundError):
        provider._validate_schema(_FakeModel(), model_path)

    assert provider.schema_validated is False
    assert provider.schema_path == (tmp_path / 'model.schema.json').as_posix()


def test_provider_rejects_feature_schema_mismatch(tmp_path: Path):
    model_path = tmp_path / 'model.ubj'
    schema_path = tmp_path / 'model.schema.json'
    bad_schema = FeatureSchema(
        version='4B.3.4',
        feature_lag=1,
        closed_candle_only=True,
        feature_pack_name='bad_pack',
        feature_columns=list(FEATURE_COLUMNS[:-1]),
        required_raw_columns=['open', 'high', 'low', 'close', 'volume'],
    )
    write_feature_schema(schema_path, bad_schema)
    provider = _provider()

    with pytest.raises(ValueError, match='Feature schema mismatch'):
        provider._validate_schema(_FakeModel(), model_path)

    assert provider.schema_validated is False


def test_provider_accepts_runtime_feature_schema(tmp_path: Path):
    model_path = tmp_path / 'model.ubj'
    schema_path = tmp_path / 'model.schema.json'
    schema = get_default_feature_schema()
    write_feature_schema(schema_path, schema)
    provider = _provider()

    provider._validate_schema(_FakeModel(), model_path)

    assert provider.schema_validated is True
    assert provider.schema_version == '4B.3.4'
    assert provider.feature_count == len(FEATURE_COLUMNS)
    assert provider.feature_lag == 1
