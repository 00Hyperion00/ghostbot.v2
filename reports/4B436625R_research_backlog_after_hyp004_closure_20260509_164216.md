# 4B.4.3.6.6.25R Research Backlog Advancement After HYP-004 Closure

- contract_version: `4B.4.3.6.6.25R`
- decision: **NEXT_HYPOTHESIS_SELECTED**
- closed_hypothesis_id: `HYP-004`
- closed_branch_name: `cross_symbol_relative_strength_rotation`
- closure_decision: `HYP004_BRANCH_CLOSURE_CONFIRMED`
- selected_next_hypothesis_id: `HYP-005`
- selected_next_hypothesis_title: `Liquidity sweep reversal with volatility compression filter`
- selected_next_branch_name: `liquidity_sweep_reversal_vol_compression`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYP004_CLOSURE_CONFIRMED', 'NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED', 'NEXT_HYPOTHESIS_AVAILABLE']`
- recommendation: HYP-004 is closed no-go. Advance research-only to HYP-005 (Liquidity sweep reversal with volatility compression filter). Do not train, reload, paper trade, or enable live trading.

## Acceptance Criteria for Next Hypothesis

- min_samples: `1500`
- min_signal_count: `45`
- min_mean_net_edge_bps: `0.0`
- min_median_net_edge_bps: `0.0`
- min_profit_factor: `1.22`
- min_walk_forward_positive_rate_pct: `62.0`
- min_oos_mean_net_edge_bps: `0.0`
- max_top_win_dependency_pct: `30.0`
- max_dominant_symbol_pct: `70.0`
- requires_robustness_gate: `True`
- requires_refinement_gate: `True`
- requires_closure_if_blocked: `True`

## Guardrails

- observation_only: `True`
- market_data_requests_performed: `False`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- Training remains blocked.
- Paper/live remain blocked.

## Policy

This gate advances the research backlog only after HYP-004 closure evidence. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.
