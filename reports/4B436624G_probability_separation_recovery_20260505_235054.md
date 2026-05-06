# 4B.4.3.6.6.24G Probability Separation / Label Calibration Recovery

- contract_version: `4B.4.3.6.6.24G`
- decision: **BLOCK**
- sample_count: `0`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- recommendation: Do not loosen thresholds yet; improve label horizon, class objective, or feature separation so BUY/SELL probabilities separate before paper trading.

## Probability Separation

- raw_distribution: `{'HOLD': 0, 'BUY': 0, 'SELL': 0}`
- raw_action_pct: `0.0`
- current_distribution: `{'HOLD': 0, 'BUY': 0, 'SELL': 0}`
- current_action_pct: `0.0`
- low_margin_rejection_pct: `0.0`
- raw_action_side_pct: `0.0`
- directional_entropy: `0.0`
- buy_sell_margin: `{'min': 0.0, 'median': 0.0, 'mean': 0.0, 'max': 0.0}`
- action_vs_hold_margin: `{'min': 0.0, 'median': 0.0, 'mean': 0.0, 'max': 0.0}`

## Label Calibration

- label_decision: `None`
- target_distribution: `None`
- target_action_rate: `None`
- predicted_action_rate: `None`
- calibrated_action_rate: `None`
- synthetic_class_padding_applied: `None`

## Reason Codes

- reason_codes: `['SEPARATION_SAMPLE_COUNT_LOW', 'RAW_ACTION_COVERAGE_LOW', 'BUY_SELL_SEPARATION_MEAN_LOW', 'BUY_SELL_SEPARATION_MEDIAN_LOW']`
- warnings: `['ACTION_VS_HOLD_MARGIN_LOW', 'CURRENT_CALIBRATION_ACTION_COVERAGE_ZERO']`

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- config_mutation_performed: `False`
- reload_performed: `False`
- order_actions_performed: `False`
- live_real_allowed: `False`

## Policy

This report never applies thresholds, reloads models, submits orders, or arms live trading. A PASS result is paper/demo evidence only.
