# 4B.4.3.6.6.28G-H1 HYP-006 Signal Frequency / Candidate Trigger Stagnation Diagnostics

- decision: `HYP006_R1_SIGNAL_FREQUENCY_STAGNATION_DIAGNOSTICS_READY`
- branch: `HYP-006-R1`
- read_only: `True`
- current_unique_observation_ids: `20`
- new_unique_observation_count_latest_delta: `0`
- stagnation_detected: `True`
- target_remaining_count: `10`

## Blockers
- `ACCEPTANCE_METRIC_FAILED_MIN_SHADOW_SAMPLE_TARGET`
- `ACCEPTANCE_METRIC_FAILED_SHADOW_WALK_FORWARD_POSITIVE_RATE_PCT`
- `ACCEPTANCE_TRACKING_REQUIREMENTS_NOT_MET`
- `NO_NEW_SHADOW_OBSERVATIONS_SINCE_28F_BASELINE`
- `PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT_NOT_PRESENT`
- `SHADOW_SAMPLE_COUNT_BELOW_TARGET`
- `HYP006_SIGNAL_FREQUENCY_STAGNATION_DETECTED`
- `CANDIDATE_SCAN_ARTIFACT_NOT_FOUND`

## Gate diagnostics
- `min_shadow_sample_target` value=`20` threshold=`30.0` passed=`False`
- `shadow_mean_forward_edge_bps` value=`108.911085` threshold=`0.0` passed=`True`
- `shadow_median_forward_edge_bps` value=`9.884293` threshold=`0.0` passed=`True`
- `shadow_profit_factor` value=`2.776782` threshold=`1.15` passed=`True`
- `shadow_walk_forward_positive_rate_pct` value=`50.0` threshold=`55.0` passed=`False`
- `shadow_data_quality_pct` value=`100.0` threshold=`99.0` passed=`True`
- `max_slippage_proxy_bps` value=`11.729452` threshold=`12.0` passed=`True`

## Recommendation

No new unique HYP-006 observations were detected across recent scheduler ledgers. Run candidate/near-miss instrumentation before any parameter relaxation; keep all trading gates closed.
