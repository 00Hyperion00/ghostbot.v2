# 4B.4.3.6.6.28G-H5 HYP-006 Counterfactual Filter Candidate Ranking

No-order gate-combo review pack. This report ranks counterfactual candidates only; it does not relax parameters or enable trading.

## Decision

- `decision`: `HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_READY`
- `read_only`: `True`
- `counterfactual_research_only`: `True`
- `approved_for_filter_candidate_review`: `True`
- `approved_for_gate_combo_counterfactual_review_candidate`: `True`
- `approved_for_parameter_relaxation_candidate`: `False`
- `approved_for_paper_candidate`: `False`
- `approved_for_live_real`: `False`
- `training_performed`: `False`
- `reload_performed`: `False`
- `trading_action_performed`: `False`
- `order_actions_performed`: `False`

## Candidate counts

- `candidate_row_count`: `29`
- `accepted_review_candidate_count`: `3`
- `watchlist_low_sample_candidate_count`: `4`
- `rejected_counterfactual_candidate_count`: `22`
- `tail_risk_flag_count`: `6`
- `do_not_relax_gate_combo_count`: `5`

## Accepted review candidates

| category | key | matured | win % | mean bps | PF | worst bps | score | tail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| symbol | BNBUSDT | 12 | 75.0 | 101.112266 | 4.267537 | -312.205541 | 59.188575 | False |
| gate_combo | MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS | 17 | 70.588235 | 160.48751 | 2.951483 | -434.018388 | 48.698976 | True |
| risk_bucket | HIGH_COMPRESSION_AND_SLIPPAGE | 17 | 70.588235 | 160.48751 | 2.951483 | -434.018388 | 48.698976 | True |

## Do-not-relax gate combos

| key | matured | win % | mean bps | PF | worst bps | reasons |
|---|---:|---:|---:|---:|---:|---|
| RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE | 38 | 34.210526 | -15.76442 | 0.842985 | -455.587378 | WIN_RATE_BELOW_REVIEW_MIN, PROFIT_FACTOR_BELOW_REVIEW_MIN, MEAN_RETURN_NOT_POSITIVE, WORST_MAE_BELOW_REVIEW_TAIL_LIMIT |
| RECLAIM_REFERENCE_CLOSE + MAX_SPREAD_SLIPPAGE_PROXY_BPS | 3 | 33.333333 | -9.312926 | 0.415166 | -31.347962 | MATURED_COUNT_BELOW_REVIEW_MIN, WIN_RATE_BELOW_REVIEW_MIN, PROFIT_FACTOR_BELOW_REVIEW_MIN, MEAN_RETURN_NOT_POSITIVE |
| RECLAIM_REFERENCE_CLOSE | 3 | 33.333333 | -37.30722 | 0.450107 | -171.091445 | MATURED_COUNT_BELOW_REVIEW_MIN, WIN_RATE_BELOW_REVIEW_MIN, PROFIT_FACTOR_BELOW_REVIEW_MIN, MEAN_RETURN_NOT_POSITIVE |
| MIN_SWEEP_DEPTH_BPS | 1 | 0.0 | -20.759354 | 0.0 | -20.759354 | MATURED_COUNT_BELOW_REVIEW_MIN, WIN_RATE_BELOW_REVIEW_MIN, PROFIT_FACTOR_BELOW_REVIEW_MIN, MEAN_RETURN_NOT_POSITIVE |
| RECLAIM_REFERENCE_CLOSE + MAX_COMPRESSION_RATIO_REFERENCE | 1 | 0.0 | -146.868251 | 0.0 | -146.868251 | MATURED_COUNT_BELOW_REVIEW_MIN, WIN_RATE_BELOW_REVIEW_MIN, PROFIT_FACTOR_BELOW_REVIEW_MIN, MEAN_RETURN_NOT_POSITIVE |

## Recommendation

Review accepted counterfactual candidates as no-order filter research only. Parameter relaxation, paper, live, training, reload, and order gates remain closed.
