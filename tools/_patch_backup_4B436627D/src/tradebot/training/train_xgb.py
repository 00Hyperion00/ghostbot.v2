from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import requests
import xgboost as xgb
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from ..features import FEATURE_COLUMNS, clean_feature_frame, get_default_feature_schema
from .calibration import apply_threshold_calibration, get_threshold_config, summarize_prediction_distribution, summarize_threshold_calibration
from .class_balance import build_sample_weights, serialize_class_weight_map
from .dataset_manifest import build_dataset_manifest, write_dataset_manifest
from .feature_schema import write_feature_schema
from .labeling import ATRLabelConfig, build_cost_aware_atr_targets


def fetch_klines(symbol: str, interval: str, days: int, base_url: str = 'https://api.binance.com') -> pd.DataFrame:
    candles_per_call = 1000
    total_candles = days * 24 * 60
    all_klines = []
    end_time = int(time.time() * 1000)
    while len(all_klines) < total_candles:
        url = f'{base_url}/api/v3/klines?symbol={symbol}&interval={interval}&limit={candles_per_call}&endTime={end_time}'
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        all_klines = data + all_klines
        end_time = data[0][0] - 1
        time.sleep(0.2)
    df = pd.DataFrame(all_klines, columns=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore'])
    return df[['open_time','close_time','open','high','low','close','volume','quote_volume']].astype(float)


def _ensure_training_matrix(
    frame: pd.DataFrame,
    feature_columns: Sequence[str] | None = None,
    target_column: str = 'target',
) -> tuple[pd.DataFrame, pd.Series]:
    cols = list(feature_columns or FEATURE_COLUMNS)
    missing = [col for col in cols if col not in frame.columns]
    if missing:
        raise ValueError(f'Missing feature columns for training matrix: {missing}')
    if target_column not in frame.columns:
        raise KeyError(f'Missing target column: {target_column}')
    clean = clean_feature_frame(frame, require_target=True, feature_columns=cols)
    X = clean[cols].copy().astype('float32')
    y = clean[target_column].copy().astype('int64')
    return X, y


def _normalize_model_path(out: str | Path) -> Path:
    path = Path(out)
    if path.suffix.lower() != '.ubj':
        path = path.with_suffix('.ubj')
    return path


def _sidecar_paths(model_path: Path) -> tuple[Path, Path]:
    stem_path = model_path.with_suffix('')
    return Path(f'{stem_path}.schema.json'), Path(f'{stem_path}.manifest.json')


def train(
    symbol: str,
    interval: str,
    days: int,
    out: str,
    base_url: str = 'https://api.binance.com',
    *,
    class_weight_profile: str = 'none',
    threshold_profile: str = 'balanced',
    feature_lag: int | None = None,
) -> dict[str, Any]:
    schema = get_default_feature_schema()
    if feature_lag is not None:
        schema.feature_lag = int(feature_lag)

    df = fetch_klines(symbol, interval, days, base_url=base_url)
    label_config = ATRLabelConfig(lookahead=10, atr_multiplier=1.5)
    labeled = build_cost_aware_atr_targets(df, config=label_config, feature_lag=schema.feature_lag)
    if labeled.empty:
        raise RuntimeError('No labeled samples produced')

    raw_target_distribution = {str(int(k)): int(v) for k, v in labeled['target'].value_counts().sort_index().to_dict().items()}
    synthetic_class_padding_applied = False
    if labeled['target'].nunique() < 3:
        # Legacy compatibility: XGBoost multi-class training needs all classes present.
        # 4B.4.3.6.6.24D explicitly reports this so candidate-quality gates can block
        # synthetic evidence instead of silently promoting a weak model.
        dummy = labeled.iloc[-3:].copy()
        dummy['target'] = [0, 1, 2]
        dummy['synthetic_class_padding'] = True
        labeled = labeled.copy()
        labeled['synthetic_class_padding'] = False
        labeled = pd.concat([labeled, dummy], ignore_index=True)
        synthetic_class_padding_applied = True

    training_target_distribution = {str(int(k)): int(v) for k, v in labeled['target'].value_counts().sort_index().to_dict().items()}

    X, y = _ensure_training_matrix(labeled, feature_columns=schema.feature_columns)
    if X.empty:
        raise RuntimeError('No clean training matrix produced')

    sample_weights, weight_map = build_sample_weights(y.tolist(), profile=class_weight_profile)
    X_train, X_test, y_train, y_test, w_train, _w_test = train_test_split(
        X, y, sample_weights, test_size=0.2, shuffle=False
    )
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=3,
        eval_metric='mlogloss',
        learning_rate=0.05,
        max_depth=3,
        n_estimators=12,
        subsample=0.85,
        colsample_bytree=0.85,
        n_jobs=1,
        tree_method='hist',
    )
    model.fit(X_train, y_train, sample_weight=w_train, eval_set=[(X_test, y_test)], verbose=False)
    proba = model.predict_proba(X_test)
    raw_pred = proba.argmax(axis=1)
    cfg = get_threshold_config(threshold_profile)
    calibrated_pred = apply_threshold_calibration(
        proba,
        raw_pred=raw_pred,
        buy_threshold=cfg.buy_threshold,
        sell_threshold=cfg.sell_threshold,
        hold_band_low=cfg.hold_band_low,
        hold_band_high=cfg.hold_band_high,
        indecision_margin=cfg.indecision_margin,
    )
    acc = accuracy_score(y_test, raw_pred)
    calibrated_acc = accuracy_score(y_test, calibrated_pred)
    prediction_distribution = summarize_prediction_distribution(y_test, raw_pred, proba)
    calibration_report = summarize_threshold_calibration(y_test, proba, raw_pred=raw_pred, profile=threshold_profile)
    validation_actual_class_distribution = dict(prediction_distribution.get('actual_class_distribution') or {})
    validation_actual_class_rate = dict(prediction_distribution.get('actual_class_rate') or {})
    validation_predicted_class_distribution = dict(prediction_distribution.get('predicted_class_distribution') or {})
    validation_predicted_class_rate = dict(prediction_distribution.get('predicted_class_rate') or {})

    out_path = _normalize_model_path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(out_path.as_posix())

    schema_path, manifest_path = _sidecar_paths(out_path)
    write_feature_schema(schema_path, schema)
    clean_labeled = clean_feature_frame(labeled, require_target=True, feature_columns=schema.feature_columns)
    manifest = build_dataset_manifest(
        symbol=symbol,
        interval=interval,
        days=days,
        schema_version=schema.version,
        feature_columns=schema.feature_columns,
        raw_df=df,
        labeled_df=labeled,
        clean_df=clean_labeled,
        target_distribution=y.value_counts().sort_index().to_dict(),
        label_config=label_config.to_dict() | {'feature_lag': schema.feature_lag},
        feature_pack_name=schema.feature_pack_name,
        class_weight_profile=class_weight_profile,
        class_weight_map=serialize_class_weight_map(weight_map),
        threshold_profile=threshold_profile,
        threshold_config=cfg.to_dict(),
    )
    write_dataset_manifest(manifest_path, manifest)

    return {
        'symbol': symbol,
        'interval': interval,
        'days': days,
        'accuracy': float(acc),
        'calibrated_accuracy': float(calibrated_acc),
        'output': out_path.as_posix(),
        'model_path': out_path.as_posix(),
        'schema_path': schema_path.as_posix(),
        'manifest_path': manifest_path.as_posix(),
        'samples': int(len(labeled)),
        'clean_samples': int(len(clean_labeled)),
        'feature_schema_version': schema.version,
        'feature_pack_name': schema.feature_pack_name,
        'feature_columns': list(schema.feature_columns),
        'feature_lag': int(schema.feature_lag),
        'class_weight_profile': str(class_weight_profile),
        'class_weight_map': serialize_class_weight_map(weight_map),
        'target_distribution': raw_target_distribution,
        'raw_target_distribution': raw_target_distribution,
        'training_target_distribution': training_target_distribution,
        'synthetic_class_padding_applied': bool(synthetic_class_padding_applied),
        'validation_actual_class_distribution': validation_actual_class_distribution,
        'validation_actual_class_rate': validation_actual_class_rate,
        'validation_predicted_class_distribution': validation_predicted_class_distribution,
        'validation_predicted_class_rate': validation_predicted_class_rate,
        'threshold_profile': str(threshold_profile),
        'threshold_config': cfg.to_dict(),
        'prediction_distribution': prediction_distribution,
        'calibrated_action_report': calibration_report['calibrated_action_report'],
        'calibrated_predicted_class_distribution': calibration_report['calibrated_predicted_class_distribution'],
        'calibrated_reason_counts': calibration_report['calibrated_reason_counts'],
        'model_format': 'ubj',
        'workflow_version': '4B.4.3.6.6.24D',
        'candidate_quality_contract_version': '4B.4.3.6.6.24D',
        'sidecars_written': True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Train XGBoost model for TradeBot')
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--interval', default='1m')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--out', required=True)
    parser.add_argument('--base-url', default='https://api.binance.com')
    parser.add_argument('--class-weight-profile', default='none')
    parser.add_argument('--threshold-profile', default='balanced')
    args = parser.parse_args()
    result = train(
        args.symbol.upper(),
        args.interval,
        args.days,
        args.out,
        base_url=args.base_url,
        class_weight_profile=args.class_weight_profile,
        threshold_profile=args.threshold_profile,
    )
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
