# 4B.4.3.6.6.25F Futures Hypothesis Branch Review / Candidate Closure Decision

- contract_version: `4B.4.3.6.6.25F`
- decision: **BRANCH_REVIEW_PENDING_COMPANION_AUDIT**
- source_reports: `9`
- primary_symbol: `BTCUSDT`
- companion_symbols: `ETHUSDT`
- interval: `4h`
- strategy: `funding_trend_exhaustion`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['COMBINED_DRY_RUN_CONFIRMATION_MISSING', 'COMBINED_TERMINAL_AUDIT_BLOCK_PRESENT', 'COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED', 'PRIMARY_CANDIDATE_TOO_SPARSE_OR_OUTLIER_DEPENDENT']`
- recommendation: Primary futures branch is too sparse or terminally blocked, while a companion exploration candidate has not been dry-run/refinement audited. Run companion audit before final closure; paper/live remain blocked.

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- training_allowed: `False`
- paper_allowed: `False`

## Branch Summaries

| symbol | latest | exploration | robustness | dry_run | refinement | terminal_block | sparse/outlier | best_phase | signals | mean_edge_bps | median_edge_bps | profit_factor | reasons |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| BTCUSDT | BLOCK | True | True | False | False | True | True | 25E | 3 | 65.519660 | 51.934953 | 99.000000 | `['BRANCH_TERMINAL_AUDIT_BLOCK', 'BRANCH_TOO_SPARSE_OR_OUTLIER_DEPENDENT', 'DRY_RUN_MEDIAN_EDGE_LOW', 'DRY_RUN_SIGNAL_COUNT_LOW', 'DRY_RUN_WALK_FORWARD_STABILITY_LOW', 'EDGE_ACTION_SIDE_IMBALANCE_HIGH', 'EDGE_OOS_EDGE_LOW', 'EDGE_SAMPLE_COUNT_LOW', 'EDGE_SIGNAL_COUNT_LOW', 'NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_OOS_EDGE_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` |
| ETHUSDT | PASS | True | True | False | False | False | False | 25C | 31 | 44.125478 | 139.208100 | 1.584716 | `['BRANCH_DRY_RUN_REFINEMENT_AUDIT_MISSING', 'EDGE_ACTION_SIDE_IMBALANCE_HIGH', 'EDGE_SAMPLE_COUNT_LOW', 'EDGE_SIGNAL_COUNT_LOW']` |

## Combined Branch Snapshot

- symbols: `BTCUSDT, ETHUSDT`
- signal_count: `34`
- weighted_mean_net_edge_bps: `46.0132`
- worst_median_net_edge_bps: `51.934953`
- min_profit_factor: `1.584716`
- all_have_exploration_pass: `True`
- dry_run_or_refinement_confirmed_count: `0`

## Candidate Evidence

| phase | symbol | interval | strategy | decision | signals | mean_edge_bps | median_edge_bps | profit_factor | reasons |
|---|---|---|---|---|---:|---:|---:|---:|---|
| 25B | ETHUSDT | 4h | funding_trend_exhaustion | BLOCK | 8 | 152.277895 | 178.849424 | 11.125555 | `['EDGE_SAMPLE_COUNT_LOW', 'EDGE_SIGNAL_COUNT_LOW', 'EDGE_ACTION_SIDE_IMBALANCE_HIGH']` |
| 25B | BTCUSDT | 4h | funding_trend_exhaustion | BLOCK | 12 | 45.621033 | 33.918707 | 2.570111 | `['EDGE_SAMPLE_COUNT_LOW', 'EDGE_SIGNAL_COUNT_LOW', 'EDGE_ACTION_SIDE_IMBALANCE_HIGH', 'EDGE_OOS_EDGE_LOW']` |
| 25B | ETHUSDT | 4h | funding_trend_exhaustion | PASS | 31 | 44.125478 | 139.208100 | 1.584716 | `[]` |
| 25B | BTCUSDT | 4h | funding_trend_exhaustion | PASS | 33 | 53.704409 | 56.665439 | 2.154669 | `[]` |
| 25C | BTCUSDT | 4h | funding_trend_exhaustion | PASS | 33 | 53.704409 | 56.665439 | 2.154669 | `[]` |
| 25C | ETHUSDT | 4h | funding_trend_exhaustion | PASS | 31 | 44.125478 | 139.208100 | 1.584716 | `[]` |
| 25C | BTCUSDT | 4h | funding_trend_exhaustion | PASS | 33 | 53.704409 | 56.665439 | 2.154669 | `[]` |
| 25C | ETHUSDT | 4h | funding_trend_exhaustion | PASS | 31 | 44.125478 | 139.208100 | 1.584716 | `[]` |
| 25D | BTCUSDT | 4h | funding_trend_exhaustion | BLOCK | 27 | 16.295166 | -23.269730 | 1.184240 | `['NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'DRY_RUN_SIGNAL_COUNT_LOW', 'DRY_RUN_MEDIAN_EDGE_LOW', 'DRY_RUN_WALK_FORWARD_STABILITY_LOW']` |
| 25D | BTCUSDT | 4h | funding_trend_exhaustion | BLOCK | 27 | 16.295166 | -23.269730 | 1.184240 | `['NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'DRY_RUN_SIGNAL_COUNT_LOW', 'DRY_RUN_MEDIAN_EDGE_LOW', 'DRY_RUN_WALK_FORWARD_STABILITY_LOW']` |
| 25E | BTCUSDT | 4h | funding_trend_exhaustion | BLOCK | 3 | 65.519660 | 51.934953 | 99.000000 | `['NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` |
| 25E | BTCUSDT | 4h | funding_trend_exhaustion | BLOCK | 3 | 64.678321 | 49.410937 | 99.000000 | `['NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` |
| 25E | BTCUSDT | 4h | funding_trend_exhaustion | BLOCK | 4 | 26.399247 | 50.012313 | 2.151512 | `['NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED', 'REFINEMENT_OOS_EDGE_LOW', 'REFINEMENT_SIDE_IMBALANCE_HIGH', 'REFINEMENT_SIGNAL_COUNT_LOW', 'REFINEMENT_TOP_WIN_DEPENDENCY_HIGH']` |

## Next Actions

- Run the same 25D/25E dry-run and refinement path for companion futures candidates before closing or continuing HYP-002.

## Policy

This branch review never trains models, reloads models, mutates config, starts paper trading, or sends orders. A continuation decision is research-only; paper/live trading remains blocked.