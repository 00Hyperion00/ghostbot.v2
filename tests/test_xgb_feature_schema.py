from pathlib import Path

from tradebot.features import FEATURE_COLUMNS, RAW_NUMERIC_COLUMNS, get_default_feature_schema
from tradebot.training.feature_schema import FEATURE_SCHEMA_VERSION, read_feature_schema, write_feature_schema



def test_default_feature_schema_matches_current_features(tmp_path: Path):
    schema = get_default_feature_schema()
    assert schema.version == FEATURE_SCHEMA_VERSION
    assert schema.feature_lag == 1
    assert schema.closed_candle_only is True
    assert schema.feature_columns == FEATURE_COLUMNS
    assert schema.required_raw_columns == RAW_NUMERIC_COLUMNS
    assert schema.feature_pack_name == 'core_price_action_regime_vwap_mtf15_v1'

    path = tmp_path / 'model.schema.json'
    write_feature_schema(path, schema)
    loaded = read_feature_schema(path)
    assert loaded.feature_columns == FEATURE_COLUMNS
    assert loaded.feature_lag == 1
    assert loaded.feature_pack_name == 'core_price_action_regime_vwap_mtf15_v1'
