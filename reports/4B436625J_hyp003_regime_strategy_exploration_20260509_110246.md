# 4B.4.3.6.6.25J HYP-003 Regime-Specific Strategy Family Exploration Gate

- contract_version: `4B.4.3.6.6.25J`
- decision: **HYP003_EXPLORATION_PASS**
- hypothesis_id: `HYP-003`
- hypothesis_title: `Regime-specific strategy family`
- hypothesis_selected_by_25i: `True`
- candidate_count: `24`
- passed_candidate_count: `2`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYP003_RESEARCH_CANDIDATE_IDENTIFIED']`
- recommendation: `HYP-003 produced a research-only regime strategy candidate. Do not train, reload, paper trade, or enable live trading; move to a dedicated robustness gate first.`

## Selected Candidate

- symbol: `ETHUSDT`
- interval: `4h`
- strategy_family: `range_mean_reversion`
- regime: `range`
- decision: `PASS`
- signal_count: `67`
- mean_net_edge_bps: `23.979025`
- median_net_edge_bps: `31.590359`
- profit_factor: `1.581891`
- oos_mean_net_edge_bps: `29.178376`
- walk_forward_positive_rate_pct: `75.0`

## Candidates

| # | decision | score | symbol | interval | family | regime | signals | mean | median | pf | oos | reasons |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | PASS | 103.821297 | ETHUSDT | 4h | range_mean_reversion | range | 67 | 23.979025 | 31.590359 | 1.581891 | 29.178376 | `[]` |
| 2 | PASS | 29.284412 | BTCUSDT | 4h | range_mean_reversion | range | 70 | 6.777121 | 2.331134 | 1.133686 | 1.815252 | `[]` |
| 3 | BLOCK | 84.643771 | SOLUSDT | 4h | low_vol_breakout_probe | low_vol | 3 | 98.628433 | 1.821076 | 4.665013 | 374.796624 | `['DIAGNOSTIC_STRATEGY_FAMILY_NOT_APPROVABLE', 'HYP003_SIGNAL_COUNT_LOW', 'HYP003_SIGNAL_COVERAGE_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 4 | BLOCK | -110.243282 | ETHUSDT | 1h | volatility_expansion_breakout | high_vol_trend | 36 | 8.763774 | -19.437791 | 1.171654 | -33.683966 | `['HYP003_MEDIAN_EDGE_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW']` |
| 5 | BLOCK | -231.300433 | SOLUSDT | 4h | range_mean_reversion | range | 63 | -14.3247 | -30.823261 | 0.808639 | -29.787484 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW']` |
| 6 | BLOCK | -265.988554 | BTCUSDT | 1h | range_mean_reversion | range | 304 | -19.082653 | -14.140526 | 0.47683 | -24.840529 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 7 | BLOCK | -272.658792 | ETHUSDT | 1h | range_mean_reversion | range | 306 | -25.705653 | -13.396401 | 0.438049 | -20.249083 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 8 | BLOCK | -287.205823 | SOLUSDT | 1h | trend_pullback_continuation | trend | 594 | -24.894481 | -27.364019 | 0.62449 | -28.434876 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 9 | BLOCK | -289.699847 | SOLUSDT | 1h | range_mean_reversion | range | 353 | -29.189677 | -21.94884 | 0.41377 | -27.537366 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 10 | BLOCK | -295.032753 | BTCUSDT | 1h | trend_pullback_continuation | trend | 587 | -25.164144 | -29.935069 | 0.501133 | -33.92937 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 11 | BLOCK | -295.597117 | BTCUSDT | 1h | volatility_expansion_breakout | high_vol_trend | 34 | -24.647174 | -37.876509 | 0.528827 | -59.514 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 12 | BLOCK | -299.51716 | ETHUSDT | 1h | trend_pullback_continuation | trend | 591 | -31.021447 | -29.567216 | 0.528504 | -60.8472 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 13 | BLOCK | -302.104961 | SOLUSDT | 1h | volatility_expansion_breakout | high_vol_trend | 43 | -25.647113 | -40.579083 | 0.647026 | -112.86289 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 14 | BLOCK | -366.05261 | ETHUSDT | 1h | low_vol_breakout_probe | low_vol | 20 | -11.583273 | -24.639321 | 0.749655 | -42.863407 | `['DIAGNOSTIC_STRATEGY_FAMILY_NOT_APPROVABLE', 'HYP003_SIGNAL_COVERAGE_LOW', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 15 | BLOCK | -389.267738 | BTCUSDT | 4h | trend_pullback_continuation | trend | 150 | -69.393489 | -59.574659 | 0.316258 | -20.861053 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 16 | BLOCK | -390.154565 | SOLUSDT | 1h | low_vol_breakout_probe | low_vol | 22 | -25.704189 | -48.545821 | 0.445612 | -73.805423 | `['DIAGNOSTIC_STRATEGY_FAMILY_NOT_APPROVABLE', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 17 | BLOCK | -419.050331 | BTCUSDT | 1h | low_vol_breakout_probe | low_vol | 18 | -29.265288 | -14.37911 | 0.226121 | -15.51997 | `['DIAGNOSTIC_STRATEGY_FAMILY_NOT_APPROVABLE', 'HYP003_SIGNAL_COUNT_LOW', 'HYP003_SIGNAL_COVERAGE_LOW', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 18 | BLOCK | -534.818186 | ETHUSDT | 4h | trend_pullback_continuation | trend | 140 | -114.833943 | -126.579004 | 0.329475 | -76.307216 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 19 | BLOCK | -591.079094 | SOLUSDT | 4h | trend_pullback_continuation | trend | 136 | -133.779141 | -150.36875 | 0.275106 | -77.507769 | `['HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW']` |
| 20 | BLOCK | -604.947396 | BTCUSDT | 4h | volatility_expansion_breakout | high_vol_trend | 10 | -121.398609 | -118.561078 | 0.143094 | -125.431394 | `['HYP003_SIGNAL_COUNT_LOW', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 21 | BLOCK | -635.628757 | BTCUSDT | 4h | low_vol_breakout_probe | low_vol | 5 | -69.969065 | -81.582939 | 0.057157 | -113.686105 | `['DIAGNOSTIC_STRATEGY_FAMILY_NOT_APPROVABLE', 'HYP003_SIGNAL_COUNT_LOW', 'HYP003_SIGNAL_COVERAGE_LOW', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_SIDE_IMBALANCE_HIGH', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 22 | BLOCK | -710.386843 | ETHUSDT | 4h | volatility_expansion_breakout | high_vol_trend | 7 | -171.682955 | -155.892012 | 0.004471 | -151.421287 | `['HYP003_SIGNAL_COUNT_LOW', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 23 | BLOCK | -739.090943 | ETHUSDT | 4h | low_vol_breakout_probe | low_vol | 4 | -112.370183 | -126.215546 | 0.086752 | -68.472108 | `['DIAGNOSTIC_STRATEGY_FAMILY_NOT_APPROVABLE', 'HYP003_SIGNAL_COUNT_LOW', 'HYP003_SIGNAL_COVERAGE_LOW', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_SIDE_IMBALANCE_HIGH', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |
| 24 | BLOCK | -814.934286 | SOLUSDT | 4h | volatility_expansion_breakout | high_vol_trend | 9 | -218.435583 | -192.500902 | 0.075088 | -258.132725 | `['HYP003_SIGNAL_COUNT_LOW', 'HYP003_MEAN_EDGE_LOW', 'HYP003_MEDIAN_EDGE_LOW', 'HYP003_PROFIT_FACTOR_LOW', 'HYP003_WIN_RATE_LOW', 'HYP003_OOS_EDGE_LOW', 'HYP003_WALK_FORWARD_STABILITY_LOW', 'HYP003_TOP_WIN_DEPENDENCY_HIGH']` |

## Guardrails

- observation_only: `True`
- public_market_data_only: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- training_allowed: `False`
- paper_allowed: `False`
- live_real_allowed: `False`
- backtest_pass_is_not_paper_permission: `True`
- paper_pass_is_not_live_permission: `True`

## Policy

This gate never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders. A PASS is research-only and must go to a later robustness gate.
