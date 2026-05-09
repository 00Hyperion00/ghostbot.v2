# 4B.4.3.6.6.25Q HYP-004 Branch Closure Evidence Pack

- contract_version: `4B.4.3.6.6.25Q`
- decision: **HYP004_BRANCH_CLOSURE_CONFIRMED**
- source_reports: `2`
- hypothesis_id: `HYP-004`
- branch_name: `cross_symbol_relative_strength_rotation`
- final_25o_decision: `HYP004_EXPLORATION_BLOCK`
- final_25p_decision: `HYP004_REFINEMENT_BLOCK`
- selected_25o_family: `UNKNOWN`
- selected_refinement_name: `UNKNOWN`
- no_approvable_exploration_candidate_confirmed: `True`
- no_approvable_refinement_candidate_confirmed: `True`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['25O_DIAGNOSTIC_STRATEGY_NOT_APPROVABLE', '25O_NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED', '25P_DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE', '25P_NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED', 'HYP004_BRANCH_CLOSED_NO_GO', 'HYP004_EXPLORATION_BLOCK_CONFIRMED', 'HYP004_REFINEMENT_BLOCK_CONFIRMED', 'NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED', 'NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED', 'NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED']`
- recommendation: HYP-004 cross-symbol relative strength branch is closed no-go. Do not train, reload, start paper trading, or enable live trading. Return to the research backlog for the next pre-registered hypothesis.

## Guardrails

- observation_only: `True`
- public_market_data_get_only: `False`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- training_allowed: `False`
- paper_allowed: `False`
- live_real_allowed: `False`

## Evidence

| phase | decision | selected | candidates | passed | signals | mean bps | median bps | pf | oos bps | reasons |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 25O | HYP004_EXPLORATION_BLOCK | UNKNOWN | 4 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | `['DIAGNOSTIC_STRATEGY_NOT_APPROVABLE', 'HYP004_MEAN_EDGE_LOW', 'HYP004_MEDIAN_EDGE_LOW', 'HYP004_OOS_EDGE_LOW', 'HYP004_PROFIT_FACTOR_LOW', 'HYP004_WALK_FORWARD_STABILITY_LOW', 'HYP004_WIN_RATE_LOW', 'NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED']` |
| 25P | HYP004_REFINEMENT_BLOCK | UNKNOWN | 5 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | `['DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE', 'HYP004_REFINED_MEAN_EDGE_LOW', 'HYP004_REFINED_MEDIAN_EDGE_LOW', 'HYP004_REFINED_OOS_EDGE_LOW', 'HYP004_REFINED_PROFIT_FACTOR_LOW', 'HYP004_REFINED_WALK_FORWARD_STABILITY_LOW', 'HYP004_REFINED_WIN_RATE_LOW', 'NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED']` |

## Registry Snapshot

- HYP-004 status: `CLOSED_NO_GO`
- Training remains blocked.
- Paper/live remain blocked.

## Policy

This closure pack never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.
