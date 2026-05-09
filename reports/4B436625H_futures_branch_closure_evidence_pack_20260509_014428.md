# 4B.4.3.6.6.25H Futures Branch Closure Evidence Pack

- contract_version: `4B.4.3.6.6.25H`
- decision: **FUTURES_BRANCH_CLOSURE_CONFIRMED**
- hypothesis_id: `HYP-002`
- branch_name: `futures_funding_trend_exhaustion`
- primary: `BTCUSDT` `4h` `funding_trend_exhaustion`
- companions: `ETHUSDT`
- source_reports: `18`
- final_25f_decision: `BRANCH_CLOSED_NO_GO`
- primary_terminal_block_count: `5`
- companion_terminal_block_count: `2`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYPOTHESIS_BRANCH_CLOSED_NO_GO', 'FINAL_25F_BRANCH_CLOSED_NO_GO', 'PRIMARY_TERMINAL_AUDIT_BLOCK_CONFIRMED', 'COMPANION_TERMINAL_AUDIT_BLOCK_CONFIRMED', 'NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED']`
- recommendation: HYP-002 funding_trend_exhaustion futures branch is closed no-go. Do not train, reload, start paper trading, or enable live trading. Restart only with a new pre-registered hypothesis.

## Terminal Block Evidence

| phase | decision | symbol | interval | strategy | signals | mean_net_edge_bps | median_net_edge_bps | profit_factor | reasons | source |
|---|---|---|---|---|---:|---:|---:|---:|---|---|
| 25D | BLOCK | BTCUSDT | 4h | funding_trend_exhaustion | 27 | 16.295166 | -23.26973 | 1.18424 | `['NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'DRY_RUN_SIGNAL_COUNT_LOW', 'DRY_RUN_MEDIAN_EDGE_LOW', 'DRY_RUN_WALK_FORWARD_STABILITY_LOW']` | `4B436625D_futures_research_candidate_simulator_20260508_082617.json` |
| 25D | BLOCK | BTCUSDT | 4h | funding_trend_exhaustion | 27 | 16.295166 | -23.26973 | 1.18424 | `['NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'DRY_RUN_SIGNAL_COUNT_LOW', 'DRY_RUN_MEDIAN_EDGE_LOW', 'DRY_RUN_WALK_FORWARD_STABILITY_LOW']` | `4B436625D_futures_research_candidate_simulator_20260508_080203.json` |
| 25E | BLOCK | BTCUSDT | 4h | funding_trend_exhaustion | 4 | 26.399247 | 50.012313 | 2.151512 | `['NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_OOS_EDGE_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_135957.json` |
| 25E | BLOCK | BTCUSDT | 4h | funding_trend_exhaustion | 3 | 64.678321 | 49.410937 | 99.0 | `['NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_105357.json` |
| 25E | BLOCK | BTCUSDT | 4h | funding_trend_exhaustion | 3 | 65.51966 | 51.934953 | 99.0 | `['NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_105302.json` |
| 25D | BLOCK | ETHUSDT | 4h | funding_trend_exhaustion | 36 | 69.5964 | 96.251131 | 1.907343 | `['NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'DRY_RUN_OOS_EDGE_LOW']` | `4B436625D_futures_research_candidate_simulator_20260508_223029.json` |
| 25E | BLOCK | ETHUSDT | 4h | funding_trend_exhaustion | 34 | -14.276254 | -6.063459 | 0.637968 | `['NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_MEAN_EDGE_LOW', 'REFINEMENT_MEDIAN_EDGE_LOW', 'REFINEMENT_OOS_EDGE_LOW', 'REFINEMENT_PROFIT_FACTOR_LOW', 'REFINEMENT_WALK_FORWARD_STABILITY_LOW', 'REFINEMENT_WIN_RATE_LOW']` | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_223031.json` |

## Evidence Chain

| phase | decision | symbol | strategy | training | paper | live | source |
|---|---|---|---|---:|---:|---:|---|
| 25B | PASS | ETHUSDT | funding_trend_exhaustion | False | False | False | `4B436625B_futures_funding_open_interest_edge_exploration_20260508_094539.json` |
| 25B | BLOCK | ETHUSDT | funding_trend_exhaustion | False | False | False | `4B436625B_futures_funding_open_interest_edge_exploration_20260508_092725.json` |
| 25C | PASS | BTCUSDT | funding_trend_exhaustion | False | False | False | `4B436625C_futures_candidate_robustness_audit_20260508_103728.json` |
| 25C | PASS | BTCUSDT | funding_trend_exhaustion | False | False | False | `4B436625C_futures_candidate_robustness_audit_20260508_103723.json` |
| 25D | BLOCK | ETHUSDT | funding_trend_exhaustion | False | False | False | `4B436625D_futures_research_candidate_simulator_20260508_223029.json` |
| 25D | BLOCK | BTCUSDT | funding_trend_exhaustion | False | False | False | `4B436625D_futures_research_candidate_simulator_20260508_082617.json` |
| 25D | BLOCK | BTCUSDT | funding_trend_exhaustion | False | False | False | `4B436625D_futures_research_candidate_simulator_20260508_080203.json` |
| 25E | BLOCK | ETHUSDT | funding_trend_exhaustion | False | False | False | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_223031.json` |
| 25E | BLOCK | BTCUSDT | funding_trend_exhaustion | False | False | False | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_135957.json` |
| 25E | BLOCK | BTCUSDT | funding_trend_exhaustion | False | False | False | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_105357.json` |
| 25E | BLOCK | BTCUSDT | funding_trend_exhaustion | False | False | False | `4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_105302.json` |
| 25F | BRANCH_CLOSED_NO_GO | None | funding_trend_exhaustion | False | False | False | `4B436625F_futures_hypothesis_branch_review_20260509_013111.json` |
| 25F | BRANCH_CLOSED_NO_GO | None | funding_trend_exhaustion | False | False | False | `4B436625F_futures_hypothesis_branch_review_20260509_013031.json` |
| 25F | BRANCH_REVIEW_PENDING_COMPANION_AUDIT | None | funding_trend_exhaustion | False | False | False | `4B436625F_futures_hypothesis_branch_review_20260509_012754.json` |
| 25F | BRANCH_REVIEW_PENDING_COMPANION_AUDIT | None | funding_trend_exhaustion | False | False | False | `4B436625F_futures_hypothesis_branch_review_20260508_171225.json` |
| 25F | BRANCH_REVIEW_PENDING_COMPANION_AUDIT | None | funding_trend_exhaustion | False | False | False | `4B436625F_futures_hypothesis_branch_review_20260508_171220.json` |
| 25G | COMPANION_AUDIT_READY | None | None | False | False | False | `4B436625G_futures_companion_candidate_audit_runner_20260508_173005.json` |
| 25G | COMPANION_AUDIT_READY | None | None | False | False | False | `4B436625G_futures_companion_candidate_audit_runner_20260508_172958.json` |

## Next Hypothesis Backlog

- Do not reuse funding_trend_exhaustion without a new pre-registered edge hypothesis and acceptance metrics.
- Prefer hypotheses with explicit OOS edge, median edge, walk-forward stability, and signal-count floors before ML retraining.
- Keep futures work observation-only until a future branch passes exploration, robustness, dry-run, refinement, and branch-review gates.

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

## Policy

This evidence pack closes the branch only at the research-record level. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.
