from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json

FEATURE_SCHEMA_VERSION = '4B.3.4'
DEFAULT_FEATURE_PACK_NAME = 'core_price_action_regime_vwap_mtf15_v1'


@dataclass(slots=True)
class FeatureSpec:
    name: str
    dtype: str = 'float32'
    required: bool = True
    source: str = 'derived'
    lag_policy: str = 't-1'
    normalization_policy: str = 'none'


@dataclass(slots=True)
class FeatureSchema:
    version: str
    feature_lag: int
    closed_candle_only: bool
    feature_columns: list[str]
    required_raw_columns: list[str]
    model_family: str = 'xgboost_multiclass'
    normalization: str = 'none'
    feature_pack_name: str = DEFAULT_FEATURE_PACK_NAME
    specs: list[FeatureSpec] = field(default_factory=list)

    @property
    def raw_numeric_columns(self) -> list[str]:
        return list(self.required_raw_columns)

    def to_dict(self) -> dict[str, Any]:
        return {
            'version': self.version,
            'feature_lag': int(self.feature_lag),
            'closed_candle_only': bool(self.closed_candle_only),
            'feature_columns': list(self.feature_columns),
            'required_raw_columns': list(self.required_raw_columns),
            'raw_numeric_columns': list(self.required_raw_columns),
            'model_family': self.model_family,
            'normalization': self.normalization,
            'feature_pack_name': self.feature_pack_name,
            'specs': [asdict(spec) for spec in self.specs],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'FeatureSchema':
        specs = [FeatureSpec(**item) for item in payload.get('specs', [])]
        return cls(
            version=str(payload.get('version') or FEATURE_SCHEMA_VERSION),
            feature_lag=int(payload.get('feature_lag', 1) or 1),
            closed_candle_only=bool(payload.get('closed_candle_only', True)),
            feature_columns=[str(item) for item in payload.get('feature_columns', [])],
            required_raw_columns=[str(item) for item in (payload.get('required_raw_columns') or payload.get('raw_numeric_columns') or [])],
            model_family=str(payload.get('model_family', 'xgboost_multiclass')),
            normalization=str(payload.get('normalization', 'none')),
            feature_pack_name=str(payload.get('feature_pack_name', DEFAULT_FEATURE_PACK_NAME)),
            specs=specs,
        )

    def validate_feature_columns(self, columns: list[str]) -> None:
        actual = list(columns)
        expected = list(self.feature_columns)
        if actual != expected:
            raise ValueError('Feature schema mismatch: ' f'expected={expected} actual={actual}')


def make_default_schema(feature_columns: list[str], raw_columns: list[str]) -> FeatureSchema:
    specs = [
        FeatureSpec(name=name, dtype='float32', required=True, source='derived', lag_policy='t-1', normalization_policy='none')
        for name in feature_columns
    ]
    return FeatureSchema(
        version=FEATURE_SCHEMA_VERSION,
        feature_lag=1,
        closed_candle_only=True,
        feature_columns=list(feature_columns),
        required_raw_columns=list(raw_columns),
        feature_pack_name=DEFAULT_FEATURE_PACK_NAME,
        specs=specs,
    )


def write_feature_schema(path: str | Path, schema: FeatureSchema) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schema.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
    return out_path


def read_feature_schema(path: str | Path) -> FeatureSchema:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    return FeatureSchema.from_dict(payload)
