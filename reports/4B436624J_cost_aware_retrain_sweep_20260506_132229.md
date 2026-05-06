# 4B.4.3.6.6.24J Cost-Aware Retrain Sweep + Separation Gate

- contract_version: `4B.4.3.6.6.24J`
- decision: **BLOCK**
- candidate_count: `6`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_model: `models/4B436624J_candidates/ETHUSDT_model_4b436624J_h30_cost16_edge30_atr3_0_balanced_action_seek_light_lagauto.ubj`
- selected_score: `-2.388763`
- selected_calibrated_action_pct: `6.530549`
- selected_buy_sell_margin_mean: `0.05313`
- selected_low_margin_rejection_pct: `1.821761`
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
| 1 | BLOCK | -34.285863 | h30_cost16_edge30_atr3_0 | balanced | balanced | 0.00386 | 56.613532 | 0.05313 | 0 | `['VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW', 'VALIDATION_CALIBRATED_ACTION_SIDE_IMBALANCE_HIGH', 'ACTION_HOLD_SEPARATION_MEAN_LOW']` | `['CALIBRATED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 2 | BLOCK | -2.388763 | h30_cost16_edge30_atr3_0 | balanced | action_seek_light | 6.530549 | 56.613532 | 0.05313 | 1.821761 | `['ACTION_HOLD_SEPARATION_MEAN_LOW']` | `[]` |
| 3 | BLOCK | -199.157328 | h30_cost16_edge30_atr3_0 | buy_sell_boost_light | balanced | 0 | 0 | 0.012073 | 0 | `['VALIDATION_RAW_ACTION_COVERAGE_LOW', 'VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW', 'BUY_SELL_SEPARATION_MEDIAN_LOW', 'ACTION_HOLD_SEPARATION_MEAN_LOW']` | `[]` |
| 4 | BLOCK | -199.157328 | h30_cost16_edge30_atr3_0 | buy_sell_boost_light | action_seek_light | 0 | 0 | 0.012073 | 0 | `['VALIDATION_RAW_ACTION_COVERAGE_LOW', 'VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW', 'BUY_SELL_SEPARATION_MEDIAN_LOW', 'ACTION_HOLD_SEPARATION_MEAN_LOW']` | `[]` |
| 5 | BLOCK | -183.157608 | h30_cost16_edge30_atr3_0 | buy_sell_boost_medium | balanced | 0 | 0 | 0.01457 | 0 | `['VALIDATION_RAW_ACTION_COVERAGE_LOW', 'VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW', 'ACTION_HOLD_SEPARATION_MEAN_LOW']` | `[]` |
| 6 | BLOCK | -183.157608 | h30_cost16_edge30_atr3_0 | buy_sell_boost_medium | action_seek_light | 0 | 0 | 0.01457 | 0 | `['VALIDATION_RAW_ACTION_COVERAGE_LOW', 'VALIDATION_CALIBRATED_ACTION_COVERAGE_LOW', 'ACTION_HOLD_SEPARATION_MEAN_LOW']` | `[]` |

## Policy

This tool may train candidate model files and write sidecars, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a candidate for manual review and later controlled reload/probe checks; real live trading remains blocked.
