# 4B.4.3.6.6.28G-H6 HYP-006 No-Order Filter Shadow Overlay Design

Accepted candidate quarantine review pack. This report designs no-order overlay candidates only; it does not change thresholds, activate runtime overlays, or enable trading.

## Decision

- `decision`: `HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_READY`
- `read_only`: `True`
- `filter_shadow_overlay_design_only`: `True`
- `approved_for_filter_shadow_overlay_candidate`: `True`
- `approved_for_quarantine_review_candidate`: `True`
- `approved_for_parameter_relaxation_candidate`: `False`
- `approved_for_paper_candidate`: `False`
- `approved_for_live_real`: `False`
- `runtime_overlay_activation_performed`: `False`
- `training_performed`: `False`
- `reload_performed`: `False`
- `trading_action_performed`: `False`
- `order_actions_performed`: `False`

## Counts

- `accepted_primary_overlay_candidate_count`: `1`
- `quarantine_review_candidate_count`: `2`
- `watchlist_overlay_candidate_count`: `5`
- `rejected_overlay_candidate_count`: `22`
- `do_not_relax_blocklist_count`: `5`

## Primary no-order overlay candidates

| category | key | overlay class | matured | win % | mean bps | PF | worst bps | status |
|---|---|---|---:|---:|---:|---:|---:|---|
| symbol | BNBUSDT | SYMBOL_FILTER_SHADOW_OVERLAY | 13 | 76.923077 | 126.61364 | 5.432608 | -312.205541 | ACCEPTED_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_CANDIDATE |

## Quarantine candidates

| category | key | matured | win % | mean bps | PF | worst bps | tail reasons |
|---|---|---:|---:|---:|---:|---:|---|
| gate_combo | MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS | 17 | 70.588235 | 160.48751 | 2.951483 | -434.018388 | WORST_RETURN_TAIL_RISK |
| risk_bucket | HIGH_COMPRESSION_AND_SLIPPAGE | 17 | 70.588235 | 160.48751 | 2.951483 | -434.018388 | WORST_RETURN_TAIL_RISK |

## Do-not-relax blocklist

| key | matured | win % | mean bps | PF | worst bps |
|---|---:|---:|---:|---:|---:|
| RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE | 37 | 35.135135 | -13.143897 | 0.86865 | -455.587378 |
| RECLAIM_REFERENCE_CLOSE + MAX_SPREAD_SLIPPAGE_PROXY_BPS | 3 | 33.333333 | -9.312926 | 0.415166 | -31.347962 |
| RECLAIM_REFERENCE_CLOSE | 3 | 33.333333 | -37.30722 | 0.450107 | -171.091445 |
| MIN_SWEEP_DEPTH_BPS | 1 | 0.0 | -20.759354 | 0.0 | -20.759354 |
| RECLAIM_REFERENCE_CLOSE + MAX_COMPRESSION_RATIO_REFERENCE | 1 | 0.0 | -146.868251 | 0.0 | -146.868251 |

## Recommendation

Use primary candidates only as no-order shadow overlay designs. Keep quarantine candidates isolated, keep do-not-relax gate combos blocked, and keep all parameter/paper/live/order gates closed.
