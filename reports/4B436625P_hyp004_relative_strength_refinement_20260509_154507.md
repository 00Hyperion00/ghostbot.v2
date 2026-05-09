# 4B.4.3.6.6.25P HYP-004 Relative Strength Candidate Refinement / Approvable Strategy Gate

- contract_version: `4B.4.3.6.6.25P`
- decision: **HYP004_REFINEMENT_BLOCK**
- hypothesis_id: `HYP-004`
- branch_name: `cross_symbol_relative_strength_rotation`
- selected_25o_family: `laggard_reversion`
- symbols: `BNBUSDT, BTCUSDT, ETHUSDT, SOLUSDT`
- candidate_count: `5`
- passed_candidate_count: `0`
- selected_refinement_name: `laggard_reversion_symbol_cooldown_lb24_h8_spread45`
- selected_signal_count: `163`
- selected_mean_net_edge_bps: `5.509956`
- selected_median_net_edge_bps: `20.545359`
- selected_profit_factor: `1.051558`
- selected_oos_mean_net_edge_bps: `41.8504`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE', 'HYP004_REFINED_MEAN_EDGE_LOW', 'HYP004_REFINED_MEDIAN_EDGE_LOW', 'HYP004_REFINED_OOS_EDGE_LOW', 'HYP004_REFINED_PROFIT_FACTOR_LOW', 'HYP004_REFINED_WALK_FORWARD_STABILITY_LOW', 'HYP004_REFINED_WIN_RATE_LOW', 'NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED']`
- recommendation: No approvable HYP-004 refined relative-strength candidate passed. Do not train, reload, paper trade, or enable live trading; close or return to backlog.

## Candidates

| refinement | decision | score | signals | mean | median | pf | oos | wf+ | dom_sym | top_win | reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| laggard_reversion_guarded_lb24_h6_spread30 | BLOCK | 29.253565 | 468 | 2.189072 | -4.246855 | 1.022718 | 23.971967 | 40.0 | 38.034188 | 9.281652 | `['HYP004_REFINED_MEAN_EDGE_LOW', 'HYP004_REFINED_MEDIAN_EDGE_LOW', 'HYP004_REFINED_PROFIT_FACTOR_LOW', 'HYP004_REFINED_WALK_FORWARD_STABILITY_LOW']` |
| laggard_reversion_guarded_lb36_h8_spread40 | BLOCK | 73.777251 | 453 | 12.039481 | 20.545359 | 1.120017 | 21.497604 | 80.0 | 34.657837 | 10.224154 | `['HYP004_REFINED_MEAN_EDGE_LOW', 'HYP004_REFINED_PROFIT_FACTOR_LOW']` |
| laggard_reversion_guarded_lb18_h4_spread35 | BLOCK | 19.4766 | 477 | 8.979457 | -12.020099 | 1.111024 | 13.377427 | 40.0 | 33.12369 | 10.890536 | `['HYP004_REFINED_MEAN_EDGE_LOW', 'HYP004_REFINED_MEDIAN_EDGE_LOW', 'HYP004_REFINED_PROFIT_FACTOR_LOW', 'HYP004_REFINED_WIN_RATE_LOW', 'HYP004_REFINED_WALK_FORWARD_STABILITY_LOW']` |
| laggard_reversion_symbol_cooldown_lb24_h8_spread45 | BLOCK | 75.964651 | 163 | 5.509956 | 20.545359 | 1.051558 | 41.8504 | 40.0 | 34.355828 | 21.571874 | `['HYP004_REFINED_MEAN_EDGE_LOW', 'HYP004_REFINED_PROFIT_FACTOR_LOW', 'HYP004_REFINED_WALK_FORWARD_STABILITY_LOW']` |
| laggard_reversion_diagnostic_loose_probe | BLOCK | -3.495054 | 500 | 1.686263 | -11.627914 | 1.023785 | -7.224133 | 40.0 | 33.4 | 10.966354 | `['DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE', 'HYP004_REFINED_MEAN_EDGE_LOW', 'HYP004_REFINED_MEDIAN_EDGE_LOW', 'HYP004_REFINED_PROFIT_FACTOR_LOW', 'HYP004_REFINED_WIN_RATE_LOW', 'HYP004_REFINED_OOS_EDGE_LOW', 'HYP004_REFINED_WALK_FORWARD_STABILITY_LOW']` |

## Policy

This gate may identify a research-only refined candidate. It never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.
