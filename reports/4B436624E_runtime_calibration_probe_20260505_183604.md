# 4B.4.3.6.6.24E Runtime Calibration Probe

- contract_version: `4B.4.3.6.6.24E`
- decision: **BLOCK**
- conclusion: `PENDING_INSUFFICIENT_SAMPLES`
- sample_count: `1`
- observation_only: `True`
- no_post_actions: `True`

## Metrics

- raw_distribution: `{'HOLD': 0, 'BUY': 1, 'SELL': 0}`
- raw_action_pct: `100.0`
- current_distribution: `{'HOLD': 1, 'BUY': 0, 'SELL': 0}`
- current_action_pct: `0.0`
- low_margin_rejection_pct: `100.0`
- relaxed_best_action_pct: `100.0`
- relaxed_best_profile: `no_margin_probe`

## Reason Codes

- reason_codes: `['PROBE_SAMPLE_COUNT_LOW', 'CURRENT_ACTION_COVERAGE_ZERO', 'LOW_MARGIN_REJECTION_HIGH']`
- warnings: `['RELAXED_THRESHOLDS_INCREASE_ACTION_COVERAGE']`

## Recommendation

Accumulate more runtime samples before changing thresholds.

## Threshold Sweep

| profile | action_pct | hold_pct | calibrated_distribution | reasons |
|---|---:|---:|---|---|
| current_runtime | 0.0 | 100.0 | `{'HOLD': 1, 'BUY': 0, 'SELL': 0}` | `{'REJECT_LOW_MARGIN': 1}` |
| runtime_default | 0.0 | 100.0 | `{'HOLD': 1, 'BUY': 0, 'SELL': 0}` | `{'REJECT_LOW_MARGIN': 1}` |
| action_seek_light | 0.0 | 100.0 | `{'HOLD': 1, 'BUY': 0, 'SELL': 0}` | `{'REJECT_LOW_MARGIN': 1}` |
| action_seek_medium | 0.0 | 100.0 | `{'HOLD': 1, 'BUY': 0, 'SELL': 0}` | `{'REJECT_LOW_MARGIN': 1}` |
| no_margin_probe | 100.0 | 0.0 | `{'HOLD': 0, 'BUY': 1, 'SELL': 0}` | `{'RAW_ACTION_FIRST_ACCEPT': 1}` |

## Guardrail

This report is diagnostic only. It does not reload models, mutate thresholds, submit orders, or arm live trading.
