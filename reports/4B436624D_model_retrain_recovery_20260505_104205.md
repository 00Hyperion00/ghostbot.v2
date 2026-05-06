# 4B.4.3.6.6.24D Model Retrain Recovery Report

- contract_version: `4B.4.3.6.6.24D`
- decision: **PASS**
- approved: `True`
- recommended_action: `PROMOTE_APPROVED_CANDIDATE`
- candidate_count: `6`

## Selection

- decision: `PASS`
- approved: `True`
- reason_codes: `[]`

## Candidates

| # | decision | score | days | class_weight | threshold | reload_allowed | reasons |
|---:|---|---:|---:|---|---|---|---|
| 1 | BLOCK | -9.5926 | 30 | balanced | balanced | False | TRAINING_GATE_BLOCK, TRAINING_ACTION_COVERAGE_LOW, TRAINING_HOLD_RATE_TOO_HIGH, TRAINING_CALIBRATED_ACCURACY_LOW |
| 2 | BLOCK | -9.7412 | 30 | balanced | action_seek_light | False | TRAINING_GATE_BLOCK, TRAINING_ACTION_COVERAGE_LOW, TRAINING_HOLD_RATE_TOO_HIGH, TRAINING_CALIBRATED_ACCURACY_LOW |
| 3 | BLOCK | -9.1319 | 30 | buy_sell_boost_light | balanced | False | TRAINING_GATE_BLOCK, TRAINING_CALIBRATED_ACCURACY_LOW |
| 4 | PASS | 1.3789 | 30 | buy_sell_boost_light | action_seek_light | True |  |
| 5 | BLOCK | -9.1235 | 30 | buy_sell_boost_medium | balanced | False | TRAINING_GATE_BLOCK, TRAINING_CALIBRATED_ACCURACY_LOW |
| 6 | PASS | 1.2592 | 30 | buy_sell_boost_medium | action_seek_light | True |  |

## Guardrail

This report never reloads a candidate model by itself. Promotion copies files only when `--promote` is explicitly provided and the best candidate is PASS.
Real live trading remains blocked by policy until later phases produce paper/live-demo evidence.
