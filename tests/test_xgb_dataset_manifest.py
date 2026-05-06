from pathlib import Path
import json

import pandas as pd

from tradebot.features import build_atr_targets, clean_feature_frame, get_default_feature_schema
from tradebot.training.dataset_manifest import build_dataset_manifest, write_dataset_manifest



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



def test_dataset_manifest_contains_schema_and_row_counts(tmp_path: Path):
    schema = get_default_feature_schema()
    raw_df = _sample_df(120)
    labeled = build_atr_targets(raw_df, lookahead=5, atr_multiplier=0.5, feature_lag=schema.feature_lag)
    clean = clean_feature_frame(labeled, require_target=True)
    manifest = build_dataset_manifest(
        symbol='ETHUSDT',
        interval='1m',
        days=1,
        schema_version=schema.version,
        feature_columns=schema.feature_columns,
        raw_df=raw_df,
        labeled_df=labeled,
        clean_df=clean,
        target_distribution=clean['target'].value_counts().sort_index().to_dict(),
        label_config={'lookahead': 5, 'atr_multiplier': 0.5},
    )
    assert manifest['schema_version'] == schema.version
    assert manifest['raw_rows'] == len(raw_df)
    assert manifest['clean_rows'] == len(clean)
    out_path = tmp_path / 'model.dataset.json'
    write_dataset_manifest(out_path, manifest)
    loaded = json.loads(out_path.read_text(encoding='utf-8'))
    assert loaded['symbol'] == 'ETHUSDT'
    assert loaded['feature_columns'] == schema.feature_columns
    assert loaded['label_config']['lookahead'] == 5



def test_dataset_manifest_includes_feature_pack_name(tmp_path):
    raw = pd.DataFrame({'open_time': [1, 2], 'close_time': [1, 2]})
    labeled = pd.DataFrame({'target': [0, 1]})
    clean = labeled.copy()
    manifest = build_dataset_manifest(
        symbol='ETHUSDT',
        interval='1m',
        days=1,
        schema_version='4B.3.4',
        feature_columns=['EMA_9'],
        raw_df=raw,
        labeled_df=labeled,
        clean_df=clean,
        target_distribution={0: 1, 1: 1},
        label_config={'lookahead': 10},
        feature_pack_name='core_price_action_regime_vwap_mtf15_v1',
    )
    assert manifest['feature_pack_name'] == 'core_price_action_regime_vwap_mtf15_v1'


def test_dataset_manifest_writes_class_weight_info(tmp_path):
    import pandas as pd
    from tradebot.training.dataset_manifest import build_dataset_manifest, write_dataset_manifest

    df = pd.DataFrame({
        'open_time': [1, 2],
        'close_time': [3, 4],
        'open': [10.0, 11.0],
        'high': [10.5, 11.5],
        'low': [9.5, 10.5],
        'close': [10.2, 11.2],
        'volume': [100.0, 101.0],
    })
    manifest = build_dataset_manifest(
        symbol='ETHUSDT',
        interval='1m',
        days=1,
        schema_version='4B.4.2',
        feature_columns=['close'],
        raw_df=df,
        labeled_df=df,
        clean_df=df,
        target_distribution={0: 1, 1: 1},
        class_weight_profile='buy_sell_boost_light',
        class_weight_map={'0': 0.9, '1': 1.15, '2': 1.15},
    )
    out = tmp_path / 'manifest.json'
    write_dataset_manifest(out, manifest)
    loaded = __import__('json').loads(out.read_text(encoding='utf-8'))
    assert loaded['class_weight_profile'] == 'buy_sell_boost_light'
    assert loaded['class_weight_map']['1'] > loaded['class_weight_map']['0']


def test_dataset_manifest_writes_threshold_profile(tmp_path):
    import pandas as pd
    df = pd.DataFrame({
        'open_time': [1, 2],
        'close_time': [3, 4],
        'open': [10.0, 11.0],
        'high': [10.5, 11.5],
        'low': [9.5, 10.5],
        'close': [10.2, 11.2],
        'volume': [100.0, 101.0],
    })
    manifest = build_dataset_manifest(
        symbol='ETHUSDT',
        interval='1m',
        days=1,
        schema_version='4B.4.3',
        feature_columns=['close'],
        raw_df=df,
        labeled_df=df,
        clean_df=df,
        target_distribution={0: 1, 1: 1},
        threshold_profile='action_seek_light',
        threshold_config={'buy_threshold': 0.58, 'sell_threshold': 0.56, 'hold_band_low': 0.42, 'hold_band_high': 0.52, 'indecision_margin': 0.05},
    )
    assert manifest['threshold_profile'] == 'action_seek_light'
    assert manifest['threshold_config']['buy_threshold'] == 0.58
