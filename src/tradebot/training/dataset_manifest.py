from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import pandas as pd

from .feature_schema import DEFAULT_FEATURE_PACK_NAME



def build_dataset_manifest(
    *,
    symbol: str,
    interval: str,
    days: int,
    schema_version: str,
    feature_columns: list[str],
    raw_df: pd.DataFrame,
    labeled_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    target_distribution: dict[int | str, int],
    label_config: dict[str, Any] | None = None,
    feature_pack_name: str | None = None,
    class_weight_profile: str = 'none',
    class_weight_map: dict[str, float] | None = None,
    threshold_profile: str = 'balanced',
    threshold_config: dict[str, float] | None = None,
) -> dict[str, Any]:
    def _safe_int(value: Any) -> int | None:
        if value is None or pd.isna(value):
            return None
        return int(value)

    manifest = {
        'symbol': symbol,
        'interval': interval,
        'days': int(days),
        'schema_version': schema_version,
        'feature_columns': list(feature_columns),
        'raw_rows': int(len(raw_df)),
        'labeled_rows': int(len(labeled_df)),
        'clean_rows': int(len(clean_df)),
        'dropped_rows': int(max(len(labeled_df) - len(clean_df), 0)),
        'start_open_time': _safe_int(raw_df['open_time'].iloc[0]) if not raw_df.empty and 'open_time' in raw_df.columns else None,
        'end_close_time': _safe_int(raw_df['close_time'].iloc[-1]) if not raw_df.empty and 'close_time' in raw_df.columns else None,
        'target_distribution': {str(k): int(v) for k, v in target_distribution.items()},
        'label_config': label_config or {},
        'feature_pack_name': feature_pack_name or DEFAULT_FEATURE_PACK_NAME,
        'class_weight_profile': str(class_weight_profile or 'none'),
        'class_weight_map': {str(k): float(v) for k, v in (class_weight_map or {}).items()},
        'threshold_profile': str(threshold_profile or 'balanced'),
        'threshold_config': {str(k): float(v) for k, v in (threshold_config or {}).items()},
    }
    return manifest



def write_dataset_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    out_path = Path(path)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return out_path
