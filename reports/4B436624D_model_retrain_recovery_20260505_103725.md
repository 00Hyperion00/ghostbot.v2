# 4B.4.3.6.6.24D Model Retrain Recovery Report

- contract_version: `4B.4.3.6.6.24D`
- decision: **PLAN**
- approved: `False`
- recommended_action: `RUN_WITHOUT_DRY_RUN`
- candidate_count: `3`

## Selection

- decision: `BLOCK`
- approved: `False`
- reason_codes: `['NO_PASSING_CANDIDATE']`

## Candidates

| # | decision | score | days | class_weight | threshold | reload_allowed | reasons |
|---:|---|---:|---:|---|---|---|---|
| 1 | DRY_RUN | 0.0000 | 30 | balanced | balanced | False | DRY_RUN_NO_TRAINING_EXECUTED |
| 2 | DRY_RUN | 0.0000 | 30 | balanced | action_seek_light | False | DRY_RUN_NO_TRAINING_EXECUTED |
| 3 | DRY_RUN | 0.0000 | 30 | buy_sell_boost_light | balanced | False | DRY_RUN_NO_TRAINING_EXECUTED |

## Guardrail

This report never reloads a candidate model by itself. Promotion copies files only when `--promote` is explicitly provided and the best candidate is PASS.
Real live trading remains blocked by policy until later phases produce paper/live-demo evidence.
