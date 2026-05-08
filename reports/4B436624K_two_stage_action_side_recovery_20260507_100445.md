# 4B.4.3.6.6.24K Two-Stage Action/Side Model Recovery

- contract_version: `4B.4.3.6.6.24K`
- decision: **BLOCK**
- candidate_count: `9`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_action_model: `models/4B436624K_candidates/ETHUSDT_two_stage_4b436624K_h5_cost8_edge10_atr1_5_action_balanced_side_balanced_ath_recall_light_sm_strict_lagauto_action.ubj`
- selected_side_model: `models/4B436624K_candidates/ETHUSDT_two_stage_4b436624K_h5_cost8_edge10_atr1_5_action_balanced_side_balanced_ath_recall_light_sm_strict_lagauto_side.ubj`
- selected_score: `55.201601`
- selected_staged_action_pct: `33.841405`
- selected_action_precision: `0.160914`
- selected_side_accuracy: `0.608078`
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
- validation_staged_action_pct: `33.841405`
- validation_action_precision: `0.160914`
- validation_action_recall: `0.757674`
- validation_action_f1: `0.265452`
- validation_side_accuracy: `0.608078`
- action_probability_gap_mean: `0.052018`
- expected_edge_proxy_bps: `-14.280958`

## Candidates

| # | decision | score | policy | action_profile | side_profile | staged_action_pct | action_precision | action_recall | side_accuracy | edge_proxy_bps | reasons | warnings |
|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | -51.474906 | h5_cost8_edge10_atr1_5 | balanced | balanced | 0.520934 | 0.339744 | 0.017124 | 0.608078 | -10.266667 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_LOW', 'ACTION_RECALL_LOW', 'ACTION_F1_LOW', 'EXPECTED_EDGE_PROXY_LOW']` | `['STAGED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 2 | BLOCK | -50.392963 | h5_cost8_edge10_atr1_5 | balanced | balanced | 0.578815 | 0.339744 | 0.017124 | 0.608078 | -10.32 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_LOW', 'ACTION_RECALL_LOW', 'ACTION_F1_LOW', 'EXPECTED_EDGE_PROXY_LOW']` | `['STAGED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 3 | BLOCK | -50.489525 | h5_cost8_edge10_atr1_5 | balanced | balanced | 0.590392 | 0.339744 | 0.017124 | 0.608078 | -10.470588 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_LOW', 'ACTION_RECALL_LOW', 'ACTION_F1_LOW', 'EXPECTED_EDGE_PROXY_LOW']` | `['STAGED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 4 | BLOCK | 46.213874 | h5_cost8_edge10_atr1_5 | balanced | balanced | 14.64017 | 0.207691 | 0.387399 | 0.608078 | -13.132314 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 5 | BLOCK | 46.188396 | h5_cost8_edge10_atr1_5 | balanced | balanced | 17.99344 | 0.207691 | 0.387399 | 0.608078 | -13.259704 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 6 | BLOCK | 46.167083 | h5_cost8_edge10_atr1_5 | balanced | balanced | 19.996141 | 0.207691 | 0.387399 | 0.608078 | -13.366268 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 7 | BLOCK | 55.201601 | h5_cost8_edge10_atr1_5 | balanced | balanced | 33.841405 | 0.160914 | 0.757674 | 0.608078 | -14.280958 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 8 | BLOCK | 23.841937 | h5_cost8_edge10_atr1_5 | balanced | balanced | 42.917229 | 0.160914 | 0.757674 | 0.608078 | -14.410358 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_HIGH', 'EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 9 | BLOCK | 19.307119 | h5_cost8_edge10_atr1_5 | balanced | balanced | 48.574185 | 0.160914 | 0.757674 | 0.608078 | -14.456625 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_HIGH', 'EXPECTED_EDGE_PROXY_LOW']` | `[]` |

## Policy

This tool may train two-stage candidate model files and write sidecars, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a candidate for manual review and later controlled reload/probe checks; real live trading remains blocked.
