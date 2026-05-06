# 4B.4.3.6.6.24F Calibration Policy Candidate Gate

- contract_version: `4B.4.3.6.6.24F`
- decision: **BLOCK**
- sample_count: `41`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_profile: `margin_relaxed_medium`
- recommendation: No safe calibration candidate passed the gate. Do not relax thresholds; collect more data or revisit model/feature calibration.

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- live_real_allowed: `False`

## Profiles

| profile | approvable | decision | score | action_pct | buy/sell/hold | dominant_action_pct | low_margin_pct | reasons | warnings |
|---|---:|---|---:|---:|---|---:|---:|---|---|
| current_runtime | False | BLOCK | -22.0 | 0.0 | BUY=0, SELL=0, HOLD=41 | 0.0 | 100.0 | `['DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'CALIBRATED_ACTION_COVERAGE_LOW', 'LOW_MARGIN_REJECTION_REMAINS_HIGH']` | `[]` |
| runtime_default | False | BLOCK | -22.0 | 0.0 | BUY=0, SELL=0, HOLD=41 | 0.0 | 100.0 | `['DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'CALIBRATED_ACTION_COVERAGE_LOW', 'LOW_MARGIN_REJECTION_REMAINS_HIGH']` | `[]` |
| action_seek_light | False | BLOCK | -22.0 | 0.0 | BUY=0, SELL=0, HOLD=41 | 0.0 | 100.0 | `['DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'CALIBRATED_ACTION_COVERAGE_LOW', 'LOW_MARGIN_REJECTION_REMAINS_HIGH']` | `[]` |
| action_seek_medium | False | BLOCK | -22.0 | 0.0 | BUY=0, SELL=0, HOLD=41 | 0.0 | 100.0 | `['DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'CALIBRATED_ACTION_COVERAGE_LOW', 'LOW_MARGIN_REJECTION_REMAINS_HIGH']` | `[]` |
| no_margin_probe | False | BLOCK | -84.517073 | 100.0 | BUY=30, SELL=11, HOLD=0 | 73.170732 | 0.0 | `['DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'ZERO_MARGIN_PROFILE_NOT_APPROVABLE', 'INDECISION_MARGIN_BELOW_FLOOR', 'CALIBRATED_ACTION_COVERAGE_TOO_HIGH']` | `['ACTION_SIDE_IMBALANCE_ELEVATED']` |
| margin_relaxed_light | True | BLOCK | -22.0 | 0.0 | BUY=0, SELL=0, HOLD=41 | 0.0 | 100.0 | `['CALIBRATED_ACTION_COVERAGE_LOW', 'LOW_MARGIN_REJECTION_REMAINS_HIGH']` | `[]` |
| margin_relaxed_medium | True | BLOCK | -13.414634 | 24.390244 | BUY=9, SELL=1, HOLD=31 | 90.0 | 75.609756 | `['ACTION_SIDE_IMBALANCE_HIGH', 'LOW_MARGIN_REJECTION_REMAINS_HIGH']` | `[]` |
| margin_relaxed_micro_guarded | True | BLOCK | -42.679746 | 56.097561 | BUY=18, SELL=5, HOLD=18 | 78.26087 | 43.902439 | `['CALIBRATED_ACTION_COVERAGE_TOO_HIGH']` | `['ACTION_SIDE_IMBALANCE_ELEVATED']` |
| action_seek_guarded | True | BLOCK | -42.679746 | 56.097561 | BUY=18, SELL=5, HOLD=18 | 78.26087 | 43.902439 | `['CALIBRATED_ACTION_COVERAGE_TOO_HIGH']` | `['ACTION_SIDE_IMBALANCE_ELEVATED', 'PAPER_ONLY_CANDIDATE_PROFILE']` |
| asymmetric_buy_sell_guarded | True | BLOCK | -42.679746 | 56.097561 | BUY=18, SELL=5, HOLD=18 | 78.26087 | 43.902439 | `['CALIBRATED_ACTION_COVERAGE_TOO_HIGH']` | `['ACTION_SIDE_IMBALANCE_ELEVATED', 'PAPER_ONLY_CANDIDATE_PROFILE']` |

## Policy

This gate never applies thresholds automatically. A PASS result only identifies a paper/demo candidate profile. Real live trading remains blocked.
