# 4B.4.3.6.6.25E Futures Candidate Refinement / Median Edge Recovery

- contract_version: `4B.4.3.6.6.25E`
- decision: **BLOCK**
- source: `binance-futures:BTCUSDT:4h:90d:funding_trend_exhaustion`
- filter_count: `8`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_filter: `funding_extreme_strict`
- selected_mean_net_edge_bps: `65.51966`
- selected_median_net_edge_bps: `51.934953`
- selected_profit_factor: `99.0`
- selected_signal_count: `3`
- recommendation: `No futures median-edge refinement candidate passed. Do not train, reload, start paper trading, or enable live trading. Tighten the hypothesis or close this candidate.`

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- backtest_pass_is_not_paper_permission: `True`
- paper_pass_is_not_live_permission: `True`

## Candidate Spec

- symbol: `BTCUSDT`
- interval: `4h`
- strategy: `funding_trend_exhaustion`
- source_phase: `4B.4.3.6.6.25D`
- horizon_bars: `1`
- round_trip_cost_bps: `16.0`
- min_edge_bps: `0.0`

## Filters

| # | decision | score | filter | signals | coverage_pct | mean_edge_bps | median_edge_bps | win_rate_pct | profit_factor | max_dd_pct | walk_pos_pct | top_win_dep_pct | reasons | warnings |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | 3444.389566 | funding_extreme_strict | 3 | 0.555556 | 65.51966 | 51.934953 | 100.0 | 99.0 | 0.0 | 100.0 | 100.0 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 2 | BLOCK | -219.3774 | funding_extreme_trend_aligned | 34 | 6.296296 | -15.745544 | -8.618232 | 47.058824 | 0.638703 | 7.825014 | 25.0 | 42.482523 | `['REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 3 | BLOCK | -286.227605 | diagnostic_base_candidate | 47 | 8.703704 | -19.187758 | -8.471076 | 42.553191 | 0.532923 | 9.98146 | 25.0 | 39.073616 | `['DIAGNOSTIC_FILTER_NOT_APPROVABLE', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_OOS_EDGE_LOW']` | `[]` |
| 4 | BLOCK | -346.952106 | funding_extreme_oi_confirmed | 25 | 4.62963 | -24.821622 | -16.597808 | 44.0 | 0.534932 | 8.157585 | 0.0 | 56.328738 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 5 | BLOCK | -404.903789 | funding_extreme_taker_confirmed | 7 | 1.296296 | -16.617428 | -10.606022 | 28.571429 | 0.440734 | 0.969903 | 50.0 | 100.0 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 6 | BLOCK | -490.153219 | funding_oi_taker_guarded | 5 | 0.925926 | -31.530186 | -38.459264 | 20.0 | 0.2013 | 0.863843 | 25.0 | 100.0 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 7 | BLOCK | -519.98408 | exhaustion_reversal_guarded | 10 | 1.851852 | -47.880639 | -66.294426 | 30.0 | 0.371012 | 6.112007 | 50.0 | 100.0 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 8 | BLOCK | -571.230236 | median_edge_recovery_guarded | 4 | 0.740741 | -69.811826 | -68.209205 | 0.0 | 0.0 | 1.748777 | 0.0 | 100.0 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |

## Policy

This tool uses public market/futures research data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a refined research candidate; paper/live trading remains blocked.
