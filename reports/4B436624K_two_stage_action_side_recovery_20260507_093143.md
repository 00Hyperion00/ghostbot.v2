# 4B.4.3.6.6.24K Two-Stage Action/Side Model Recovery

- contract_version: `4B.4.3.6.6.24K`
- decision: **BLOCK**
- candidate_count: `6`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_action_model: `models/4B436624K_candidates/ETHUSDT_two_stage_4b436624K_h5_cost8_edge10_atr1_5_action_balanced_side_balanced_ath_balanced_sm_guarded_lagauto_action.ubj`
- selected_side_model: `models/4B436624K_candidates/ETHUSDT_two_stage_4b436624K_h5_cost8_edge10_atr1_5_action_balanced_side_balanced_ath_balanced_sm_guarded_lagauto_side.ubj`
- selected_score: `45.963976`
- selected_staged_action_pct: `16.515532`
- selected_action_precision: `0.210487`
- selected_side_accuracy: `0.607166`
- recommendation: No two-stage action/side candidate passed. Revisit action features, meta-labels, side objective, or regime split before promote/reload.

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- promotion_requires_explicit_flag: `True`

## Selected Candidate Metrics

- reason_codes: `['EXPECTED_EDGE_PROXY_LOW']`
- validation_staged_action_pct: `16.515532`
- validation_action_precision: `0.210487`
- validation_action_recall: `0.362815`
- validation_action_f1: `0.266414`
- validation_side_accuracy: `0.607166`
- action_probability_gap_mean: `0.052404`
- expected_edge_proxy_bps: `-13.113084`

## Candidates

| # | decision | score | policy | action_profile | side_profile | staged_action_pct | action_precision | action_recall | side_accuracy | edge_proxy_bps | reasons | warnings |
|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | 45.963976 | h5_cost8_edge10_atr1_5 | balanced | balanced | 16.515532 | 0.210487 | 0.362815 | 0.607166 | -13.113084 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 2 | BLOCK | 45.951417 | h5_cost8_edge10_atr1_5 | balanced | balanced | 18.429481 | 0.210487 | 0.362815 | 0.607166 | -13.175879 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 3 | BLOCK | 24.900317 | h5_cost8_edge10_atr1_5 | balanced | balanced | 42.114605 | 0.163201 | 0.752421 | 0.607166 | -14.239692 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_HIGH', 'EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 4 | BLOCK | 20.140988 | h5_cost8_edge10_atr1_5 | balanced | balanced | 48.033957 | 0.163201 | 0.752421 | 0.607166 | -14.358933 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_HIGH', 'EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 5 | BLOCK | 45.963976 | h5_cost8_edge10_atr1_5 | balanced | side_balance_guarded | 16.515532 | 0.210487 | 0.362815 | 0.607166 | -13.113084 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 6 | BLOCK | 45.951417 | h5_cost8_edge10_atr1_5 | balanced | side_balance_guarded | 18.429481 | 0.210487 | 0.362815 | 0.607166 | -13.175879 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |

## Policy

This tool may train two-stage candidate model files and write sidecars, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a candidate for manual review and later controlled reload/probe checks; real live trading remains blocked.
