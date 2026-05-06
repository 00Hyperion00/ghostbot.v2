# 4B.4.3.6.6.24J Cost-Aware Retrain Sweep + Separation Gate

- contract_version: `4B.4.3.6.6.24J`
- decision: **BLOCK**
- candidate_count: `3`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_model: `models/4B436624J_candidates/ETHUSDT_model_4b436624J_h30_cost16_edge30_atr3_0_balanced_action_seek_light_lagauto.ubj`
- selected_score: `-1.545546`
- selected_calibrated_action_pct: `7.742483`
- selected_buy_sell_margin_mean: `0.052463`
- selected_low_margin_rejection_pct: `1.694392`
- promoted_to: `None`
- recommendation: No cost-aware retrain candidate passed the separation gate. Do not promote/reload; revisit policy, features, or model objective.

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- promotion_requires_explicit_flag: `True`

## Candidates

| # | decision | score | policy | class_weight | threshold | calibrated_action_pct | raw_action_pct | buy_sell_margin_mean | low_margin_pct | reasons | warnings |
|---:|---|---:|---|---|---|---:|---:|---:|---:|---|---|
| 1 | BLOCK | -34.280192 | h30_cost16_edge30_atr3_0 | balanced | balanced | 0.027018 | 56.146513 | 0.052463 | 0.007719 | `['VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW', 'VALIDATION_CALIBRATED_ACTION_SIDE_IMBALANCE_HIGH', 'ACTION_HOLD_SEPARATION_MEAN_LOW']` | `['CALIBRATED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 2 | BLOCK | -1.545546 | h30_cost16_edge30_atr3_0 | balanced | action_seek_light | 7.742483 | 56.146513 | 0.052463 | 1.694392 | `['ACTION_HOLD_SEPARATION_MEAN_LOW']` | `[]` |
| 3 | BLOCK | -198.188151 | h30_cost16_edge30_atr3_0 | buy_sell_boost_light | balanced | 0 | 0 | 0.012449 | 0 | `['VALIDATION_RAW_ACTION_COVERAGE_LOW', 'VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW', 'BUY_SELL_SEPARATION_MEDIAN_LOW', 'ACTION_HOLD_SEPARATION_MEAN_LOW']` | `[]` |

## Policy

This tool may train candidate model files and write sidecars, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a candidate for manual review and later controlled reload/probe checks; real live trading remains blocked.
