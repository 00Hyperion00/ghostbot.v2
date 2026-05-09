# 4B.4.3.6.6.25N Research Backlog Advancement After HYP-003 Closure

- contract_version: `4B.4.3.6.6.25N`
- decision: **NEXT_HYPOTHESIS_SELECTED**
- closed_hypothesis_id: `HYP-003`
- closed_branch_name: `regime_specific_strategy_family`
- selected_next_hypothesis_id: `HYP-004`
- selected_next_hypothesis_title: `Cross-symbol relative strength rotation`
- selected_next_branch_name: `cross_symbol_relative_strength_rotation`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYP003_CLOSURE_CONFIRMED', 'NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED', 'NEXT_HYPOTHESIS_AVAILABLE']`
- recommendation: HYP-003 is closed no-go. Advance research-only to HYP-004 (Cross-symbol relative strength rotation). Do not train, reload, paper trade, or enable live trading.

## Acceptance Criteria for Next Hypothesis

- min_samples: `1500`
- min_signal_count: `50`
- min_mean_net_edge_bps: `0.0`
- min_median_net_edge_bps: `0.0`
- min_profit_factor: `1.2`
- min_walk_forward_positive_rate_pct: `60.0`
- min_oos_mean_net_edge_bps: `0.0`
- max_top_win_dependency_pct: `32.0`
- max_dominant_side_pct: `80.0`
- requires_robustness_gate: `True`
- requires_closure_if_blocked: `True`

## Guardrails

- observation_only: `True`
- market_data_requests_performed: `False`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- training_allowed: `False`
- paper_allowed: `False`
- backtest_pass_is_not_paper_permission: `True`
- paper_pass_is_not_live_permission: `True`

## Policy

This gate only advances the research backlog after a confirmed HYP-003 closure. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.
