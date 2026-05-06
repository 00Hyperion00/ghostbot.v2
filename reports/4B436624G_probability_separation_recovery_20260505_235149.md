# 4B.4.3.6.6.24G Probability Separation / Label Calibration Recovery

- contract_version: `4B.4.3.6.6.24G`
- decision: **BLOCK**
- sample_count: `41`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- recommendation: Do not loosen thresholds yet; improve label horizon, class objective, or feature separation so BUY/SELL probabilities separate before paper trading.

## Probability Separation

- raw_distribution: `{'HOLD': 0, 'BUY': 30, 'SELL': 11}`
- raw_action_pct: `100.0`
- current_distribution: `{'HOLD': 41, 'BUY': 0, 'SELL': 0}`
- current_action_pct: `0.0`
- low_margin_rejection_pct: `100.0`
- raw_action_side_pct: `73.170732`
- directional_entropy: `0.839004`
- buy_sell_margin: `{'min': 0.00231573, 'median': 0.00652888, 'mean': 0.00624104, 'max': 0.01478896}`
- action_vs_hold_margin: `{'min': 0.2826024, 'median': 0.34570964, 'mean': 0.33327686, 'max': 0.36638775}`

## Label Calibration

- label_decision: `BLOCK`
- target_distribution: `None`
- target_action_rate: `1.0`
- predicted_action_rate: `1.0`
- calibrated_action_rate: `1.0`
- synthetic_class_padding_applied: `False`

## Reason Codes

- reason_codes: `['RAW_ACTION_COVERAGE_TOO_HIGH', 'BUY_SELL_SEPARATION_MEAN_LOW', 'BUY_SELL_SEPARATION_MEDIAN_LOW', 'LOW_MARGIN_REJECTION_HIGH']`
- warnings: `['RAW_ACTION_SIDE_IMBALANCE_ELEVATED', 'CURRENT_CALIBRATION_ACTION_COVERAGE_ZERO']`

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- config_mutation_performed: `False`
- reload_performed: `False`
- order_actions_performed: `False`
- live_real_allowed: `False`

## Policy

This report never applies thresholds, reloads models, submits orders, or arms live trading. A PASS result is paper/demo evidence only.
