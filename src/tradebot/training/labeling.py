from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from ..features import build_atr_targets, build_feature_frame, clean_feature_frame


@dataclass(slots=True)
class ATRLabelConfig:
    lookahead: int = 10
    atr_multiplier: float = 1.5
    entry_fee_bps: float = 0.0
    exit_fee_bps: float = 0.0
    entry_slippage_bps: float = 0.0
    exit_slippage_bps: float = 0.0
    min_profit_bps: float = 0.0
    use_high_low_barriers: bool = True
    ambiguous_barrier_policy: str = 'hold'

    @property
    def round_trip_cost_bps(self) -> float:
        return float(self.entry_fee_bps + self.exit_fee_bps + self.entry_slippage_bps + self.exit_slippage_bps)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload['round_trip_cost_bps'] = self.round_trip_cost_bps
        return payload


def build_cost_aware_atr_targets(
    df: pd.DataFrame,
    config: ATRLabelConfig | None = None,
    *,
    feature_lag: int = 1,
) -> pd.DataFrame:
    cfg = config or ATRLabelConfig()
    min_profit_bps = max(float(cfg.min_profit_bps), float(cfg.round_trip_cost_bps))
    labeled = build_atr_targets(
        df,
        lookahead=cfg.lookahead,
        atr_multiplier=cfg.atr_multiplier,
        feature_lag=feature_lag,
        min_profit_bps=min_profit_bps,
        use_high_low_barriers=cfg.use_high_low_barriers,
        ambiguous_barrier_policy=cfg.ambiguous_barrier_policy,
    )
    label_config = cfg.to_dict()
    # Runtime/training reports use this value as the effective round-trip floor.
    # It must include either explicit costs or the configured minimum profit floor.
    label_config['round_trip_cost_bps'] = float(min_profit_bps)
    label_config['feature_lag'] = int(feature_lag or 0)
    label_config['effective_min_profit_bps'] = float(min_profit_bps)
    labeled.attrs['label_config'] = label_config
    return labeled


__all__ = ['ATRLabelConfig', 'build_cost_aware_atr_targets', 'build_feature_frame', 'clean_feature_frame']
