# 4B.4.3.6.6.25O HYP-004 Cross-Symbol Relative Strength Exploration Gate

- contract_version: `4B.4.3.6.6.25O`
- decision: **HYP004_EXPLORATION_BLOCK**
- hypothesis_id: `HYP-004`
- branch_name: `cross_symbol_relative_strength_rotation`
- symbols: `BNBUSDT, BTCUSDT, ETHUSDT, SOLUSDT`
- candidate_count: `4`
- passed_candidate_count: `0`
- selected_strategy_family: `laggard_reversion`
- selected_signal_count: `510`
- selected_mean_net_edge_bps: `21.936463`
- selected_median_net_edge_bps: `9.812974`
- selected_profit_factor: `1.238365`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['DIAGNOSTIC_STRATEGY_NOT_APPROVABLE', 'HYP004_MEAN_EDGE_LOW', 'HYP004_MEDIAN_EDGE_LOW', 'HYP004_OOS_EDGE_LOW', 'HYP004_PROFIT_FACTOR_LOW', 'HYP004_WALK_FORWARD_STABILITY_LOW', 'HYP004_WIN_RATE_LOW', 'NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED']`
- recommendation: No HYP-004 relative-strength candidate passed exploration. Do not train, reload, paper trade, or enable live trading; refine or close this hypothesis.

## Candidates

| strategy | decision | score | signals | mean | median | pf | oos | wf+ | dom_sym | top_win | reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| leader_long_momentum | BLOCK | -5.772063 | 510 | -7.024781 | -8.430782 | 0.9367 | 25.336252 | 50.0 | 30.784314 | 5.500283 | `['HYP004_MEAN_EDGE_LOW', 'HYP004_MEDIAN_EDGE_LOW', 'HYP004_PROFIT_FACTOR_LOW', 'HYP004_WALK_FORWARD_STABILITY_LOW']` |
| laggard_reversion | BLOCK | 42.941262 | 510 | 21.936463 | 9.812974 | 1.238365 | 29.363216 | 50.0 | 35.490196 | 5.933846 | `['HYP004_WALK_FORWARD_STABILITY_LOW']` |
| leader_laggard_spread | BLOCK | -54.202736 | 510 | -30.480622 | -25.751509 | 0.405879 | -18.013482 | 0.0 | 16.470588 | 7.296481 | `['HYP004_MEAN_EDGE_LOW', 'HYP004_MEDIAN_EDGE_LOW', 'HYP004_PROFIT_FACTOR_LOW', 'HYP004_WIN_RATE_LOW', 'HYP004_OOS_EDGE_LOW', 'HYP004_WALK_FORWARD_STABILITY_LOW']` |
| short_term_rotation_probe | BLOCK | -19.106813 | 528 | -8.797258 | -14.721585 | 0.882406 | 9.252398 | 0.0 | 26.704545 | 6.036605 | `['DIAGNOSTIC_STRATEGY_NOT_APPROVABLE', 'HYP004_MEAN_EDGE_LOW', 'HYP004_MEDIAN_EDGE_LOW', 'HYP004_PROFIT_FACTOR_LOW', 'HYP004_WIN_RATE_LOW', 'HYP004_WALK_FORWARD_STABILITY_LOW']` |

## Guardrails

- No model training.
- No model reload.
- No config mutation.
- No paper trading.
- No live trading.
- No order actions.
