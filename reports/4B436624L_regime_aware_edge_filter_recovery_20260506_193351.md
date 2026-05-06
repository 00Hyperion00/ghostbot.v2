# 4B.4.3.6.6.24L Regime-Aware Edge Filter Recovery

- contract_version: `4B.4.3.6.6.24L`
- decision: **BLOCK**
- candidate_count: `9`
- candidate_run_count: `6`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_filter: `high_volume_pressure`
- selected_score: `17.885125`
- selected_filtered_action_pct: `11.302335`
- selected_action_precision: `0.212359`
- selected_side_accuracy: `0.655949`
- selected_expected_edge_proxy_bps: `-12.985319`
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

- validation_staged_action_pct: `40.598109`
- validation_action_precision: `0.168615`
- validation_action_recall: `0.562817`
- validation_side_accuracy: `0.63867`
- expected_edge_proxy_bps: `-14.123182`

## Selected Filter Metrics

- reason_codes: `['REGIME_FILTER_EXPECTED_EDGE_LOW']`
- filtered_action_count: `2929`
- filtered_action_pct: `11.302335`
- action_precision: `0.212359`
- action_precision_lift: `0.043744`
- action_recall: `0.197335`
- filtered_side_accuracy: `0.655949`
- filtered_action_side_pct: `52.099693`
- expected_edge_proxy_bps: `-12.985319`

## Filter Candidates

| # | decision | score | filter | family | action_pct | precision | precision_lift | side_accuracy | edge_proxy_bps | reasons | warnings |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | -15.103246 | all_staged_actions | diagnostic | 40.598109 | 0.168615 | 0 | 0.63867 | -14.123182 | `['DIAGNOSTIC_FILTER_NOT_APPROVABLE', 'REGIME_FILTER_ACTION_COVERAGE_HIGH', 'REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 2 | BLOCK | -10.602511 | mtf_trend_aligned | trend | 34.898707 | 0.168952 | 0.000337 | 0.635471 | -14.134896 | `['REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 3 | BLOCK | -23.601129 | ema_vwap_aligned | trend | 13.725642 | 0.173461 | 0.004846 | 0.648298 | -13.951645 | `['REGIME_FILTER_SIDE_IMBALANCE_HIGH', 'REGIME_FILTER_DIRECTIONAL_ENTROPY_LOW', 'REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 4 | BLOCK | 17.885125 | high_volume_pressure | volume | 11.302335 | 0.212359 | 0.043744 | 0.655949 | -12.985319 | `['REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 5 | BLOCK | 8.220356 | atr_expansion_non_range | volatility | 15.928999 | 0.179264 | 0.010648 | 0.666216 | -13.700581 | `['REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 6 | BLOCK | -3.858097 | rsi_mid_trend | momentum | 23.820181 | 0.163454 | -0.005161 | 0.61447 | -14.384254 | `['REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 7 | BLOCK | 10.790044 | trend_strength_top_quartile | trend | 13.47868 | 0.174921 | 0.006306 | 0.703764 | -13.568279 | `['REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 8 | BLOCK | -10.701652 | vwap_breakout_side | vwap | 34.38935 | 0.17123 | 0.002615 | 0.634993 | -14.085727 | `['REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |
| 9 | BLOCK | 7.041102 | low_range_high_trend | regime | 15.774648 | 0.169276 | 0.000661 | 0.689306 | -13.799413 | `['REGIME_FILTER_ACTION_PRECISION_LOW', 'REGIME_FILTER_PRECISION_LIFT_LOW', 'REGIME_FILTER_EXPECTED_EDGE_LOW']` | `[]` |

## Policy

This tool may train temporary two-stage candidates for validation and regime analysis, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a training-candidate regime filter for manual review; real live trading remains blocked.
