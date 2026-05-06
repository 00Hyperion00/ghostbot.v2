# 4B.4.3.6.6.24F Calibration Policy Candidate Gate

- contract_version: `4B.4.3.6.6.24F`
- decision: **BLOCK**
- sample_count: `0`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_profile: `margin_relaxed_light`
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
| current_runtime | False | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| runtime_default | False | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| action_seek_light | False | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| action_seek_medium | False | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| no_margin_probe | False | BLOCK | -18.2 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'DIAGNOSTIC_PROFILE_NOT_APPROVABLE', 'ZERO_MARGIN_PROFILE_NOT_APPROVABLE', 'INDECISION_MARGIN_BELOW_FLOOR', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| margin_relaxed_light | True | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| margin_relaxed_medium | True | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| margin_relaxed_micro_guarded | True | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `[]` |
| action_seek_guarded | True | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `['PAPER_ONLY_CANDIDATE_PROFILE']` |
| asymmetric_buy_sell_guarded | True | BLOCK | -18.0 | 0.0 | BUY=0, SELL=0, HOLD=0 | 0.0 | 0.0 | `['CALIBRATION_GATE_SAMPLE_COUNT_LOW', 'RAW_ACTION_COVERAGE_ZERO', 'CALIBRATED_ACTION_COVERAGE_LOW']` | `['PAPER_ONLY_CANDIDATE_PROFILE']` |

## Policy

This gate never applies thresholds automatically. A PASS result only identifies a paper/demo candidate profile. Real live trading remains blocked.
