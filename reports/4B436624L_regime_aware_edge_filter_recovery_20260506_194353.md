# 4B.4.3.6.6.24L Regime-Aware Edge Filter Recovery

- contract_version: `4B.4.3.6.6.24L`
- decision: **BLOCK**
- candidate_count: `9`
- candidate_run_count: `9`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_filter: `trend_strength_top_quartile`
- selected_score: `22.683382`
- selected_filtered_action_pct: `0.683028`
- selected_action_precision: `0.316384`
- selected_side_accuracy: `0.732143`
- selected_expected_edge_proxy_bps: `-9.661017`
- recommendation: No regime-aware positive-edge filter passed. Revisit regime features, meta-labels, costs, or model objective before promote/reload.

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- promotion_requires_explicit_flag: `True`

## Baseline

- validation_staged_action_pct: `1.539708`
- validation_action_precision: `0.280702`
- validation_action_recall: `0.035544`
- validation_side_accuracy: `0.696429`
- expected_edge_proxy_bps: `-10.962406`

## Selected Filter Metrics

- reason_codes: `['REGIME_FILTER_ACTION_COVERAGE_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']`
- filtered_action_count: `177`
- filtered_action_pct: `0.683028`
- action_precision: `0.316384`
- action_precision_lift: `0.035682`
- action_recall: `0.017772`
- filtered_side_accuracy: `0.732143`
- filtered_action_side_pct: `62.711864`
- expected_edge_proxy_bps: `-9.661017`

## Filter Candidates

| # | decision | score | filter | family | action_pct | precision | precision_lift | side_accuracy | edge_proxy_bps | reasons | warnings |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | 12.95946 | all_staged_actions | diagnostic | 1.539708 | 0.280702 | 0 | 0.696429 | -10.962406 | `['DIAGNOSTIC_FILTER_NOT_APPROVABLE', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 2 | BLOCK | 16.384606 | mtf_trend_aligned | trend | 1.300455 | 0.290801 | 0.010099 | 0.714286 | -10.522255 | `['REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |
| 3 | BLOCK | -7.319766 | ema_vwap_aligned | trend | 0.879833 | 0.298246 | 0.017544 | 0.735294 | -10.105263 | `['REGIME_FILTER_ACTION_COVERAGE_LOW', 'REGIME_FILTER_SIDE_IMBALANCE_HIGH', 'REGIME_FILTER_DIRECTIONAL_ENTROPY_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |
| 4 | BLOCK | 15.251647 | high_volume_pressure | volume | 0.937717 | 0.296296 | 0.015595 | 0.666667 | -10.888889 | `['REGIME_FILTER_ACTION_COVERAGE_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |
| 5 | BLOCK | 9.328764 | atr_expansion_non_range | volatility | 0.949294 | 0.272358 | -0.008344 | 0.686567 | -11.268293 | `['REGIME_FILTER_ACTION_COVERAGE_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |
| 6 | BLOCK | 10.782769 | rsi_mid_trend | momentum | 0.690746 | 0.268156 | -0.012545 | 0.708333 | -11.162011 | `['REGIME_FILTER_ACTION_COVERAGE_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |
| 7 | BLOCK | 22.683382 | trend_strength_top_quartile | trend | 0.683028 | 0.316384 | 0.035682 | 0.732143 | -9.661017 | `['REGIME_FILTER_ACTION_COVERAGE_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |
| 8 | BLOCK | 8.39053 | vwap_breakout_side | vwap | 1.412364 | 0.278689 | -0.002013 | 0.696078 | -11.016393 | `['REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |
| 9 | BLOCK | 14.643906 | low_range_high_trend | regime | 0.752489 | 0.297436 | 0.016734 | 0.672414 | -10.8 | `['REGIME_FILTER_ACTION_COVERAGE_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `['REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR']` |

## Policy

This tool may train temporary two-stage candidates for validation and regime analysis, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a training-candidate regime filter for manual review; real live trading remains blocked.
