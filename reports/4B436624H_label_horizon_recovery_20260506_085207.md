# 4B.4.3.6.6.24H Label Horizon / Target Engineering Recovery

- contract_version: `4B.4.3.6.6.24H`
- decision: **BLOCK**
- sample_count: `43200`
- policy_count: `10`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_policy: `h3_atr0_8_fast`
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
| current_baseline_h10_atr1_5 | False | BLOCK | -97.103236 | 43161 | 87.6254 | 12.3746 | BUY=19095, SELL=18725, HOLD=5341 | 50.4892 | 0.9999 | 22.0804 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW', 'DIAGNOSTIC_POLICY_NOT_APPROVABLE']` | `[]` |
| h3_atr0_8_fast | True | BLOCK | -75.689065 | 43168 | 81.8940 | 18.1060 | BUY=17910, SELL=17442, HOLD=7816 | 50.6619 | 0.9999 | 12.2596 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h5_atr0_9_fast_balanced | True | BLOCK | -91.199465 | 43166 | 89.8971 | 10.1029 | BUY=19544, SELL=19261, HOLD=4361 | 50.3646 | 1.0000 | 14.5650 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h5_atr1_1_balanced | True | BLOCK | -76.397971 | 43166 | 82.7758 | 17.2242 | BUY=17993, SELL=17738, HOLD=7435 | 50.3568 | 1.0000 | 16.4908 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h10_atr1_0_balanced | True | BLOCK | -104.468738 | 43161 | 96.5965 | 3.4035 | BUY=20918, SELL=20774, HOLD=1469 | 50.1727 | 1.0000 | 16.2827 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h10_atr1_25_balanced | True | BLOCK | -96.524712 | 43161 | 92.9844 | 7.0156 | BUY=20206, SELL=19927, HOLD=3028 | 50.3476 | 1.0000 | 19.2088 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h15_atr1_25_directional | True | BLOCK | -105.081337 | 43156 | 97.1777 | 2.8223 | BUY=21116, SELL=20822, HOLD=1218 | 50.3505 | 1.0000 | 19.6162 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h15_atr1_5_directional | True | BLOCK | -99.204597 | 43156 | 94.5755 | 5.4245 | BUY=20617, SELL=20198, HOLD=2341 | 50.5133 | 0.9999 | 22.4770 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h20_atr1_5_directional_strong | True | BLOCK | -104.610904 | 43151 | 97.1889 | 2.8111 | BUY=21190, SELL=20748, HOLD=1213 | 50.5270 | 0.9999 | 22.5558 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |
| h20_atr1_8_directional_strong | True | BLOCK | -97.65089 | 43151 | 94.1624 | 5.8376 | BUY=20538, SELL=20094, HOLD=2519 | 50.5464 | 0.9999 | 26.2507 | `['TARGET_ACTION_COVERAGE_HIGH', 'TARGET_HOLD_COVERAGE_LOW']` | `[]` |

## Policy

This tool never changes label settings, retrains, reloads, mutates config, or sends orders. A PASS only identifies a training-candidate label policy; paper/live trading remains blocked.
