# 4B.4.3.6.6.24K Two-Stage Action/Side Model Recovery

- contract_version: `4B.4.3.6.6.24K`
- decision: **BLOCK**
- candidate_count: `9`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_action_model: `models/4B436624K_candidates/ETHUSDT_two_stage_4b436624K_h5_cost8_edge10_atr1_5_action_balanced_side_balanced_ath_recall_light_sm_strict_lagauto_action.ubj`
- selected_side_model: `models/4B436624K_candidates/ETHUSDT_two_stage_4b436624K_h5_cost8_edge10_atr1_5_action_balanced_side_balanced_ath_recall_light_sm_strict_lagauto_side.ubj`
- selected_score: `56.656514`
- selected_staged_action_pct: `32.865136`
- selected_action_precision: `0.165422`
- selected_side_accuracy: `0.61497`
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
- validation_staged_action_pct: `32.865136`
- validation_action_precision: `0.165422`
- validation_action_recall: `0.75896`
- validation_action_f1: `0.271639`
- validation_side_accuracy: `0.61497`
- action_probability_gap_mean: `0.053345`
- expected_edge_proxy_bps: `-13.959141`

## Candidates

| # | decision | score | policy | action_profile | side_profile | staged_action_pct | action_precision | action_recall | side_accuracy | edge_proxy_bps | reasons | warnings |
|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | -37.770265 | h5_cost8_edge10_atr1_5 | balanced | balanced | 1.030291 | 0.30273 | 0.038693 | 0.61497 | -11.52809 | `['ACTION_RECALL_LOW', 'ACTION_F1_LOW', 'EXPECTED_EDGE_PROXY_LOW']` | `['STAGED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 2 | BLOCK | -32.082893 | h5_cost8_edge10_atr1_5 | balanced | balanced | 1.366004 | 0.30273 | 0.038693 | 0.61497 | -12.40678 | `['ACTION_RECALL_LOW', 'ACTION_F1_LOW', 'EXPECTED_EDGE_PROXY_LOW']` | `['STAGED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 3 | BLOCK | -30.218774 | h5_cost8_edge10_atr1_5 | balanced | balanced | 1.462473 | 0.30273 | 0.038693 | 0.61497 | -12.205805 | `['ACTION_RECALL_LOW', 'ACTION_F1_LOW', 'EXPECTED_EDGE_PROXY_LOW']` | `['STAGED_ACTION_COVERAGE_NEAR_FLOOR']` |
| 4 | BLOCK | 46.849954 | h5_cost8_edge10_atr1_5 | balanced | balanced | 13.297318 | 0.212402 | 0.370441 | 0.61497 | -13.016831 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 5 | BLOCK | 46.956404 | h5_cost8_edge10_atr1_5 | balanced | balanced | 17.352884 | 0.212402 | 0.370441 | 0.61497 | -13.260841 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 6 | BLOCK | 46.94082 | h5_cost8_edge10_atr1_5 | balanced | balanced | 18.954274 | 0.212402 | 0.370441 | 0.61497 | -13.338762 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 7 | BLOCK | 56.656514 | h5_cost8_edge10_atr1_5 | balanced | balanced | 32.865136 | 0.165422 | 0.75896 | 0.61497 | -13.959141 | `['EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 8 | BLOCK | 25.076574 | h5_cost8_edge10_atr1_5 | balanced | balanced | 43.168049 | 0.165422 | 0.75896 | 0.61497 | -14.186645 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_HIGH', 'EXPECTED_EDGE_PROXY_LOW']` | `[]` |
| 9 | BLOCK | 21.225796 | h5_cost8_edge10_atr1_5 | balanced | balanced | 47.945205 | 0.165422 | 0.75896 | 0.61497 | -14.331911 | `['TWO_STAGE_STAGED_ACTION_COVERAGE_HIGH', 'EXPECTED_EDGE_PROXY_LOW']` | `[]` |

## Policy

This tool may train two-stage candidate model files and write sidecars, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a candidate for manual review and later controlled reload/probe checks; real live trading remains blocked.
