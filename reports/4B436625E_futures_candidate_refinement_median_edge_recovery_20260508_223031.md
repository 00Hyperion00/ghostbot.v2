# 4B.4.3.6.6.25E Futures Candidate Refinement / Median Edge Recovery

- contract_version: `4B.4.3.6.6.25E`
- decision: **BLOCK**
- source: `binance-futures:ETHUSDT:4h:90d:funding_trend_exhaustion`
- filter_count: `8`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_filter: `funding_extreme_strict`
- selected_mean_net_edge_bps: `-14.276254`
- selected_median_net_edge_bps: `-6.063459`
- selected_profit_factor: `0.637968`
- selected_signal_count: `34`
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

- symbol: `ETHUSDT`
- interval: `4h`
- strategy: `funding_trend_exhaustion`
- source_phase: `4B.4.3.6.6.25D`
- horizon_bars: `1`
- round_trip_cost_bps: `16.0`
- min_edge_bps: `0.0`

## Filters

| # | decision | score | filter | signals | coverage_pct | mean_edge_bps | median_edge_bps | win_rate_pct | profit_factor | max_dd_pct | walk_pos_pct | top_win_dep_pct | reasons | warnings |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | -212.824285 | funding_extreme_strict | 34 | 6.296296 | -14.276254 | -6.063459 | 41.176471 | 0.637968 | 6.65189 | 25.0 | 47.753866 | `['REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 2 | BLOCK | -235.25669 | funding_extreme_oi_confirmed | 30 | 5.555556 | -15.44571 | -19.612582 | 36.666667 | 0.62612 | 6.487868 | 50.0 | 53.572916 | `['REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 3 | BLOCK | -238.610227 | funding_extreme_trend_aligned | 47 | 8.703704 | -26.87525 | -9.59047 | 40.425532 | 0.462742 | 12.770202 | 25.0 | 38.211383 | `['REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_OOS_EDGE_LOW']` | `[]` |
| 4 | BLOCK | -309.127284 | diagnostic_base_candidate | 63 | 11.666667 | -26.907241 | -26.117449 | 34.920635 | 0.428996 | 17.090396 | 0.0 | 32.871878 | `['DIAGNOSTIC_FILTER_NOT_APPROVABLE', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_OOS_EDGE_LOW']` | `[]` |
| 5 | BLOCK | -376.987409 | exhaustion_reversal_guarded | 16 | 2.962963 | -41.721991 | -20.664861 | 37.5 | 0.317551 | 5.649035 | 25.0 | 73.149994 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 6 | BLOCK | -442.843672 | funding_extreme_taker_confirmed | 20 | 3.703704 | -38.832354 | -44.33369 | 25.0 | 0.180898 | 8.138026 | 0.0 | 78.337676 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 7 | BLOCK | -496.609677 | median_edge_recovery_guarded | 13 | 2.407407 | -45.840064 | -43.969677 | 7.692308 | 0.061993 | 5.604876 | 0.0 | 100.0 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |
| 8 | BLOCK | -500.820131 | funding_oi_taker_guarded | 13 | 2.407407 | -48.483138 | -44.697703 | 7.692308 | 0.058812 | 5.948476 | 0.0 | 100.0 | `['REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WIN_RATE_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH', 'REFINEMENT_OOS_EDGE_LOW']` | `['REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR']` |

## Policy

This tool uses public market/futures research data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a refined research candidate; paper/live trading remains blocked.
