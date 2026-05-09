# 4B.4.3.6.6.25M HYP-003 Branch Closure Evidence Pack

- contract_version: `4B.4.3.6.6.25M`
- decision: **HYP003_BRANCH_CLOSURE_CONFIRMED**
- hypothesis_id: `HYP-003`
- branch_name: `regime_specific_strategy_family`
- selected_candidate: `UNKNOWN`
- source_reports: `5`
- final_25j_decision: `HYP003_EXPLORATION_PASS`
- final_25k_decision: `HYP003_ROBUSTNESS_BLOCK`
- final_25l_decision: `HYP003_BRANCH_CLOSURE_RECOMMENDED`
- exploration_pass_confirmed: `True`
- robustness_block_confirmed: `True`
- branch_closure_recommended_confirmed: `True`
- no_alternate_candidate_confirmed: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYP003_EXPLORATION_PASS_CONFIRMED', 'HYP003_ROBUSTNESS_BLOCK_CONFIRMED', 'HYP003_ROBUSTNESS_TERMINAL_CODES_CONFIRMED', 'HYP003_BRANCH_CLOSURE_RECOMMENDED_CONFIRMED', 'NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE_CONFIRMED', 'HYP003_25L_TERMINAL_CODES_CONFIRMED', 'HYP003_SELECTED_CANDIDATE_CONSISTENT', 'NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED']`
- recommendation: HYP-003 branch is closed no-go. Do not train, reload, start paper trading, or enable live trading. Return to the research backlog for the next pre-registered hypothesis.

## Guardrails

- observation_only: `True`
- market_data_requests_performed: `False`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- training_allowed: `False`
- paper_allowed: `False`
- live_real_allowed: `False`

## Evidence Chain

| phase | decision | source | research | training | paper | live | reasons | selected |
|---|---|---|---:|---:|---:|---:|---|---|
| 25J | HYP003_EXPLORATION_PASS | 4B436625J_hyp003_regime_strategy_exploration_20260509_110246.json | True | False | False | False | `['HYP003_RESEARCH_CANDIDATE_IDENTIFIED']` | `ETHUSDT 4h range_mean_reversion range` |
| 25K | HYP003_ROBUSTNESS_BLOCK | 4B436625K_hyp003_robustness_walkforward_confirmation_20260509_113143.json | False | False | False | False | `['ROBUST_MEAN_EDGE_LOW', 'ROBUST_MEDIAN_EDGE_LOW', 'ROBUST_OOS_EDGE_LOW', 'ROBUST_PROFIT_FACTOR_LOW', 'ROBUST_WALK_FORWARD_STABILITY_LOW', 'ROBUST_WIN_RATE_LOW']` | `UNKNOWN` |
| 25L | HYP003_BRANCH_CLOSURE_RECOMMENDED | 4B436625L_hyp003_candidate_refinement_branch_decision_20260509_144721.json | False | False | False | False | `['HYP003_SELECTED_CANDIDATE_ROBUSTNESS_BLOCK', 'NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE', 'ROBUST_MEAN_EDGE_LOW', 'ROBUST_MEDIAN_EDGE_LOW', 'ROBUST_OOS_EDGE_LOW', 'ROBUST_PROFIT_FACTOR_LOW', 'ROBUST_WALK_FORWARD_STABILITY_LOW', 'ROBUST_WIN_RATE_LOW']` | `UNKNOWN` |
| 25L | HYP003_BRANCH_CLOSURE_RECOMMENDED | 4B436625L_hyp003_candidate_refinement_branch_decision_20260509_144725.json | False | False | False | False | `['HYP003_SELECTED_CANDIDATE_ROBUSTNESS_BLOCK', 'NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE', 'ROBUST_MEAN_EDGE_LOW', 'ROBUST_MEDIAN_EDGE_LOW', 'ROBUST_OOS_EDGE_LOW', 'ROBUST_PROFIT_FACTOR_LOW', 'ROBUST_WALK_FORWARD_STABILITY_LOW', 'ROBUST_WIN_RATE_LOW']` | `UNKNOWN` |
| 25L | HYP003_BRANCH_CLOSURE_RECOMMENDED | 4B436625L_hyp003_candidate_refinement_branch_decision_20260509_145634.json | False | False | False | False | `['HYP003_SELECTED_CANDIDATE_ROBUSTNESS_BLOCK', 'NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE', 'ROBUST_MEAN_EDGE_LOW', 'ROBUST_MEDIAN_EDGE_LOW', 'ROBUST_OOS_EDGE_LOW', 'ROBUST_PROFIT_FACTOR_LOW', 'ROBUST_WALK_FORWARD_STABILITY_LOW', 'ROBUST_WIN_RATE_LOW']` | `UNKNOWN` |

## Registry Snapshot

- status: `CLOSED_NO_GO`
- next_registry_action: `RETURN_TO_BACKLOG_FOR_NEXT_HYPOTHESIS_SELECTION`

## Policy

This evidence pack never fetches market data, trains models, reloads models, mutates config, starts paper trading, or sends orders. Paper/live remain blocked.
