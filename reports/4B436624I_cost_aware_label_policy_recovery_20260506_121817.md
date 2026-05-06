# 4B.4.3.6.6.24I Cost-Aware Label Policy Recovery

- contract_version: `4B.4.3.6.6.24I`
- decision: **PASS**
- sample_count: `129600`
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
| diagnostic_h5_atr1_1_cost0_edge0 | False | BLOCK | -90.873516 | 129566 | 82.0300 | 17.9700 | BUY=53369, SELL=52914, HOLD=23283 | 50.2141 | 21.8722 | 10.8987 | 0.0000 | `['EFFECTIVE_MIN_PROFIT_BELOW_COST_FLOOR', 'TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW', 'DIAGNOSTIC_POLICY_NOT_APPROVABLE']` | `[]` |
| h5_cost8_edge10_atr1_5 | True | PASS | 38.18696 | 129566 | 12.2378 | 87.7622 | BUY=8000, SELL=7856, HOLD=113710 | 50.4541 | 72.2137 | 17.6210 | 18.0000 | `[]` | `[]` |
| h10_cost8_edge15_atr1_8 | True | PASS | 43.824706 | 129561 | 17.5392 | 82.4608 | BUY=11471, SELL=11253, HOLD=106837 | 50.4797 | 92.1083 | 22.7250 | 23.0000 | `[]` | `['TARGET_ACTION_RATE_NEAR_TARGET']` |
| h10_cost12_edge15_atr2_0 | True | PASS | 42.278024 | 129561 | 12.8333 | 87.1667 | BUY=8424, SELL=8203, HOLD=112934 | 50.6646 | 105.2907 | 25.2710 | 27.0000 | `[]` | `[]` |
| h15_cost12_edge20_atr2_0 | True | PASS | 44.487413 | 129556 | 16.9378 | 83.0622 | BUY=11230, SELL=10714, HOLD=107612 | 51.1757 | 116.9918 | 26.4314 | 32.0000 | `[]` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h15_cost16_edge20_atr2_5 | True | PASS | 43.770511 | 129556 | 11.6699 | 88.3301 | BUY=7726, SELL=7393, HOLD=114437 | 51.1013 | 136.9449 | 31.9268 | 36.0000 | `[]` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h20_cost16_edge25_atr2_5 | True | PASS | 45.155503 | 129551 | 14.2330 | 85.7670 | BUY=9368, SELL=9071, HOLD=111112 | 50.8054 | 147.0239 | 31.9242 | 41.0000 | `[]` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h20_cost20_edge30_atr3_0 | True | BLOCK | 36.585462 | 129551 | 8.8560 | 91.1440 | BUY=5874, SELL=5599, HOLD=118078 | 51.1985 | 178.0209 | 38.6376 | 50.0000 | `['TARGET_HOLD_DOMINANCE_HIGH']` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h30_cost16_edge30_atr3_0 | True | PASS | 48.079381 | 129541 | 17.1452 | 82.8548 | BUY=11299, SELL=10911, HOLD=107331 | 50.8735 | 165.3351 | 36.4947 | 46.0000 | `[]` | `['TARGET_ACTION_RATE_NEAR_TARGET', 'HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |
| h30_cost20_edge40_atr3_5 | True | BLOCK | 37.721891 | 129541 | 9.9629 | 90.0371 | BUY=6547, SELL=6359, HOLD=116635 | 50.7283 | 207.7741 | 43.8720 | 60.0000 | `['TARGET_HOLD_DOMINANCE_HIGH']` | `['HIGH_EDGE_FILTER_MAY_REDUCE_TRAINING_ACTIONS']` |

## Policy

This tool never changes label settings, retrains, reloads, mutates config, starts paper trading, or sends orders. A PASS only identifies a training-candidate cost-aware label policy; paper/live trading remains blocked.
