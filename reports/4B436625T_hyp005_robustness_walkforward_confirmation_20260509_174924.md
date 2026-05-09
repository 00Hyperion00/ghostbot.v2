# 4B.4.3.6.6.25T HYP-005 Robustness / Walk-Forward Confirmation Gate

- contract_version: `4B.4.3.6.6.25T`
- decision: **HYP005_ROBUSTNESS_PASS**
- hypothesis_id: `HYP-005`
- branch_name: `liquidity_sweep_reversal_vol_compression`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- signal_count: `28`
- mean_net_edge_bps: `140.089198`
- penalized_mean_net_edge_bps: `122.089198`
- median_net_edge_bps: `109.881101`
- profit_factor: `4.197094`
- win_rate_pct: `82.142857`
- oos_mean_net_edge_bps: `104.924999`
- walk_forward_positive_rate_pct: `75.0`
- top_win_dependency_pct: `36.380414`
- dominant_symbol_pct: `35.714286`
- wick_dependency_pct: `0.0`
- recent_30d_signal_count: `21`
- recent_30d_mean_edge_bps: `98.77503`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `[]`
- warnings: `['ROBUST_SMALL_SAMPLE_PENALTY_APPLIED']`
- recommendation: HYP-005 liquidity sweep reversal candidate passed robustness/walk-forward as a research-only candidate. Do not train, reload, paper trade, or enable live trading; move to a dedicated no-order shadow planning/spec gate first.

## Guardrails

- observation_only: `True`
- public_market_data_get_only: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- Training remains blocked.
- Paper/live remain blocked.
