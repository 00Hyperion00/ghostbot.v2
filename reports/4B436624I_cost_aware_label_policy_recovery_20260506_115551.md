# 4B.4.3.6.6.24I Cost-Aware Label Policy Recovery

- contract_version: `4B.4.3.6.6.24I`
- decision: **PASS**
- sample_count: `43200`
- policy_count: `10`
- approved_for_training_candidate: `True`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_policy: `h30_cost16_edge30_atr3_0`
- recommendation: A cost-aware label policy passed the training-candidate gate. Use it only for a controlled retrain sweep; do not start paper/live trading yet.

## Guardrails

- observation_only: `True`
- get_only_public_market_data: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`

## Policies

| policy | approvable | decision | score | samples | action_pct | hold_pct | buy/sell/hold | side_pct | fwd_gap_bps | min_net_edge_bps | effective_floor_bps | reasons | warnings |
|---|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|
| diagnostic_h5_atr1_1_cost0_edge0 | False | BLOCK | -94.315742 | 43166 | 82.7966 | 17.2034 | BUY=18021, SELL=17719, HOLD=7426 | 50.4225 | 16.4733 | 8.1162 | 0.0000 | `['EFFECTIVE_MIN_PROFIT_BELOW_COST_FLOOR', 'TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW', 'DIAGNOSTIC_POLICY_NOT_APPROVABLE']` | `[]` |
| h5_cost8_edge10_atr1_5 | True | BLOCK | 24.779683 | 43166 | 8.4279 | 91.5721 | BUY=1844, SELL=1794, HOLD=39528 | 50.6872 | 61.5204 | 12.6411 | 18.0000 | `['TARGET_HOLD_DOMINANCE_HIGH']` | `[]` |
| h10_cost8_edge15_atr1_8 | True | PASS | 38.325524 | 43161 | 12.4487 | 87.5513 | BUY=2769, SELL=2604, HOLD=37788 | 51.5355 | 78.3581 | 15.9329 | 23.0000 | `[]` | `[]` |
| h10_cost12_edge15_atr2_0 | True | BLOCK | 29.210225 | 43161 | 8.9039 | 91.0961 | BUY=1984, SELL=1859, HOLD=39318 | 51.6263 | 88.9551 | 17.1682 | 27.0000 | `['TARGET_HOLD_DOMINANCE_HIGH']` | `[]` |
| h15_cost12_edge20_atr2_0 | True | PASS | 38.243446 | 43156 | 11.8361 | 88.1639 | BUY=2683, SELL=2425, HOLD=38048 | 52.5254 | 99.2984 | 17.0373 | 32.0000 | `[]` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h15_cost16_edge20_atr2_5 | True | BLOCK | 30.191119 | 43156 | 8.1333 | 91.8667 | BUY=1790, SELL=1720, HOLD=39646 | 50.9972 | 113.9732 | 20.3870 | 36.0000 | `['TARGET_HOLD_DOMINANCE_HIGH']` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h20_cost16_edge25_atr2_5 | True | BLOCK | 31.194805 | 43151 | 9.8005 | 90.1995 | BUY=2144, SELL=2085, HOLD=38922 | 50.6976 | 124.0570 | 20.6369 | 41.0000 | `['TARGET_HOLD_DOMINANCE_HIGH']` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h20_cost20_edge30_atr3_0 | True | BLOCK | 18.093012 | 43151 | 5.8145 | 94.1855 | BUY=1282, SELL=1227, HOLD=40642 | 51.0961 | 149.9015 | 24.8218 | 50.0000 | `['TARGET_ACTION_COVERAGE_LOW', 'TARGET_HOLD_DOMINANCE_HIGH']` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h30_cost16_edge30_atr3_0 | True | PASS | 41.640044 | 43141 | 12.2899 | 87.7101 | BUY=2636, SELL=2666, HOLD=37839 | 50.2829 | 141.0076 | 23.6895 | 46.0000 | `[]` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h30_cost20_edge40_atr3_5 | True | BLOCK | 21.248125 | 43141 | 6.2446 | 93.7554 | BUY=1380, SELL=1314, HOLD=40447 | 51.2249 | 182.4978 | 31.2486 | 60.0000 | `['TARGET_ACTION_COVERAGE_LOW', 'TARGET_HOLD_DOMINANCE_HIGH']` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |

## Policy

This tool never changes label settings, retrains, reloads, mutates config, starts paper trading, or sends orders. A PASS only identifies a training-candidate cost-aware label policy; paper/live trading remains blocked.
