# 4B.4.3.6.6.28G-H2 HYP-006 Candidate / Near-Miss Scan Instrumentation

- decision: `HYP006_R1_CANDIDATE_NEAR_MISS_SCAN_INSTRUMENTATION_READY`
- branch_id: `HYP-006-R1`
- read_only: `True`
- raw_candidate_scan_artifact_found: `False`
- candidate_count: `0`
- near_miss_count: `0`
- trigger_count: `0`
- current_unique_observation_ids: `20`
- new_unique_observation_count_latest_delta: `0`
- target_remaining_count: `10`

## Gate block counter

- `SAMPLE_TARGET`: `6`
- `WALK_FORWARD_POSITIVE_RATE`: `4`
- `ACCEPTANCE_TRACKING_REQUIREMENTS_NOT_MET`: `2`
- `NO_NEW_SHADOW_OBSERVATIONS_SINCE_28F_BASELINE`: `2`
- `PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT_NOT_PRESENT`: `2`
- `CANDIDATE_SCAN_ARTIFACT_NOT_FOUND`: `1`
- `HYP006_SIGNAL_FREQUENCY_STAGNATION_DETECTED`: `1`

## Symbol candidate counter

- No raw symbol candidate data was available.

## Recommendation

Raw HYP-006 candidate/near-miss scan artifacts are still required before any parameter relaxation. Keep no-order collection running and add integrated raw scan hooks only through a separate read-only research gate if missing.

## Safety

This report is read-only and does not approve parameter relaxation, paper trading, live trading, model reload, training, or order placement.
