# 4B.4.3.6.6.24H Label Horizon / Target Engineering Recovery

- contract_version: `4B.4.3.6.6.24H`
- decision: **BLOCK**
- sample_count: `129600`
- policy_count: `10`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_policy: `h5_atr1_1_balanced`
- recommendation: No safe label horizon / target policy passed. Revisit horizon, ATR multiplier, costs, or feature separation before retraining.

## Guardrails

- observation_only: `True`
- get_only_public_market_data: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`

## Policies

| policy | approvable | decision | score | samples | action_pct | hold_pct | buy/sell/hold | side_pct | entropy | fwd_gap_bps | reasons | warnings |
|---|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| current_baseline_h10_atr1_5 | False | BLOCK | -93.407534 | 129561 | 86.6318 | 13.3682 | BUY=56411, SELL=55830, HOLD=17320 | 50.2588 | 1.0000 | 30.0826 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW', 'DIAGNOSTIC_POLICY_NOT_APPROVABLE']` | `[]` |
| h3_atr0_8_fast | True | BLOCK | -74.564726 | 129568 | 81.7740 | 18.2260 | BUY=53288, SELL=52665, HOLD=23615 | 50.2940 | 1.0000 | 16.0603 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h5_atr0_9_fast_balanced | True | BLOCK | -89.693993 | 129566 | 89.6315 | 10.3685 | BUY=58359, SELL=57773, HOLD=13434 | 50.2523 | 1.0000 | 19.2902 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h5_atr1_1_balanced | True | BLOCK | -73.678218 | 129566 | 82.0123 | 17.9877 | BUY=53338, SELL=52922, HOLD=23306 | 50.1957 | 1.0000 | 22.1469 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h10_atr1_0_balanced | True | BLOCK | -103.375346 | 129561 | 96.6101 | 3.3899 | BUY=62748, SELL=62421, HOLD=4392 | 50.1306 | 1.0000 | 21.8292 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h10_atr1_25_balanced | True | BLOCK | -94.430999 | 129561 | 92.6691 | 7.3309 | BUY=60229, SELL=59834, HOLD=9498 | 50.1645 | 1.0000 | 26.1108 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h15_atr1_25_directional | True | BLOCK | -103.380254 | 129556 | 97.1055 | 2.8945 | BUY=63068, SELL=62738, HOLD=3750 | 50.1312 | 1.0000 | 26.8090 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h15_atr1_5_directional | True | BLOCK | -96.24394 | 129556 | 94.0497 | 5.9503 | BUY=61083, SELL=60764, HOLD=7709 | 50.1309 | 1.0000 | 31.0377 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h20_atr1_5_directional_strong | True | BLOCK | -102.080708 | 129551 | 96.9132 | 3.0868 | BUY=62978, SELL=62574, HOLD=3999 | 50.1609 | 1.0000 | 31.4822 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h20_atr1_8_directional_strong | True | BLOCK | -93.741091 | 129551 | 93.3702 | 6.6298 | BUY=60454, SELL=60508, HOLD=8589 | 50.0223 | 1.0000 | 36.5463 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |

## Policy

This tool never changes label settings, retrains, reloads, mutates config, or sends orders. A PASS only identifies a training-candidate label policy; paper/live trading remains blocked.
