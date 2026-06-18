# 4B.4.3.6.6.28G-H7 HYP-006 No-Order Overlay Simulation: BNBUSDT Primary Filter Shadow Measurement

This pack measures the H6 BNBUSDT primary overlay candidate in no-order research mode only. It does not activate runtime filtering, change parameters, train, reload, or enable paper/live trading.

## Decision

- `decision`: `NO_ORDER_BNBUSDT_PRIMARY_OVERLAY_SHADOW_MEASUREMENT_READY`
- `read_only`: `True`
- `overlay_simulation_measurement_only`: `True`
- `approved_for_overlay_shadow_measurement`: `True`
- `approved_for_runtime_overlay_activation_candidate`: `False`
- `approved_for_parameter_relaxation_candidate`: `False`
- `approved_for_paper_candidate`: `False`
- `approved_for_live_real`: `False`
- `runtime_overlay_activation_performed`: `False`
- `training_performed`: `False`
- `reload_performed`: `False`
- `trading_action_performed`: `False`
- `order_actions_performed`: `False`

## Primary measurement summary

- `symbol`: `BNBUSDT`
- `measurement_candidate_present`: `True`
- `measurement_guard_pass`: `True`
- `matured_count`: `12`
- `win_rate_pct`: `75.0`
- `mean_return_bps`: `101.112266`
- `profit_factor`: `4.267537`
- `worst_return_bps`: `-312.205541`
- `worst_mae_bps`: `-426.691375`
- `net_return_bps`: `1213.347189`
- `measurement_guard_reasons`: `[]`

## Primary measurement candidate

| key | matured | win % | mean bps | PF | worst bps | worst MAE | status |
|---|---:|---:|---:|---:|---:|---:|---|
| BNBUSDT | 12 | 75.0 | 101.112266 | 4.267537 | -312.205541 | -426.691375 | MEASUREMENT_GUARD_PASS |

## Exclusions

### Quarantine candidates
| category | key | matured | mean bps | PF | reason |
|---|---|---:|---:|---:|---|
| gate_combo | MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS | 17 | 160.48751 | 2.951483 | TAIL_RISK_QUARANTINE_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT |
| risk_bucket | HIGH_COMPRESSION_AND_SLIPPAGE | 17 | 160.48751 | 2.951483 | TAIL_RISK_QUARANTINE_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT |

### Watchlist candidates
| category | key | matured | mean bps | PF | reason |
|---|---|---:|---:|---:|---|
| gate_combo | MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE | 9 | 258.042239 | 18.702614 | LOW_SAMPLE_WATCHLIST_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT |
| risk_bucket | HIGH_COMPRESSION_LOW_WICK | 9 | 258.042239 | 18.702614 | LOW_SAMPLE_WATCHLIST_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT |
| gate_combo | MIN_WICK_PCT_REFERENCE | 6 | 154.735419 | 9.664283 | LOW_SAMPLE_WATCHLIST_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT |
| risk_bucket | LOW_WICK | 6 | 154.735419 | 9.664283 | LOW_SAMPLE_WATCHLIST_NOT_USED_IN_H7_BNBUSDT_MEASUREMENT |

### Do-not-relax blocklist
| category | key | matured | mean bps | PF | reason |
|---|---|---:|---:|---:|---|
| gate_combo | RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE | 38 | -15.76442 | 0.842985 | EXPLICIT_DO_NOT_RELAX_BLOCKLIST_ENFORCED |
| gate_combo | RECLAIM_REFERENCE_CLOSE + MAX_SPREAD_SLIPPAGE_PROXY_BPS | 3 | -9.312926 | 0.415166 | EXPLICIT_DO_NOT_RELAX_BLOCKLIST_ENFORCED |
| gate_combo | RECLAIM_REFERENCE_CLOSE | 3 | -37.30722 | 0.450107 | EXPLICIT_DO_NOT_RELAX_BLOCKLIST_ENFORCED |
| gate_combo | MIN_SWEEP_DEPTH_BPS | 1 | -20.759354 | 0.0 | EXPLICIT_DO_NOT_RELAX_BLOCKLIST_ENFORCED |
| gate_combo | RECLAIM_REFERENCE_CLOSE + MAX_COMPRESSION_RATIO_REFERENCE | 1 | -146.868251 | 0.0 | EXPLICIT_DO_NOT_RELAX_BLOCKLIST_ENFORCED |

## Recommendation

Keep BNBUSDT overlay in no-order shadow measurement only. Do not activate runtime overlay, do not relax parameters, and keep paper/live/order gates closed.
