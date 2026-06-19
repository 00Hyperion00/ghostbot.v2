# 4B.4.3.6.6.28G-H4 HYP-006 Near-Miss Outcome Attribution

- decision: `HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_READY`
- branch_id: `HYP-006-R1`
- read_only: `True`
- counterfactual_research_only: `True`
- attributed_near_miss_event_count: `100`
- matured_near_miss_event_count: `100`
- near_miss_mean_return_bps: `77.310992`
- near_miss_win_rate_pct: `50.0`
- trigger_benchmark_mean_return_bps: `108.911085`
- trigger_benchmark_win_rate_pct: `50.0`
- approved_for_parameter_relaxation_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`

## Gate combo outcome summary

- `MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS`: count `17`, matured `17`, mean `160.48751`, win_rate `70.588235`, pf `2.951483`, research_candidate `True`
- `MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE`: count `9`, matured `9`, mean `258.042239`, win_rate `77.777778`, pf `18.702614`, research_candidate `True`
- `MIN_SWEEP_DEPTH_BPS + MIN_WICK_PCT_REFERENCE`: count `7`, matured `7`, mean `88.17779`, win_rate `57.142857`, pf `1.78504`, research_candidate `True`
- `MIN_WICK_PCT_REFERENCE`: count `6`, matured `6`, mean `154.735419`, win_rate `66.666667`, pf `9.664283`, research_candidate `True`
- `RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE`: count `38`, matured `38`, mean `-15.76442`, win_rate `34.210526`, pf `0.842985`, research_candidate `False`
- `MAX_COMPRESSION_RATIO_REFERENCE`: count `10`, matured `10`, mean `142.291167`, win_rate `50.0`, pf `5.303371`, research_candidate `False`
- `MIN_SWEEP_DEPTH_BPS + MAX_COMPRESSION_RATIO_REFERENCE`: count `4`, matured `4`, mean `94.760811`, win_rate `50.0`, pf `5.220696`, research_candidate `False`
- `RECLAIM_REFERENCE_CLOSE + MAX_SPREAD_SLIPPAGE_PROXY_BPS`: count `3`, matured `3`, mean `-9.312926`, win_rate `33.333333`, pf `0.415166`, research_candidate `False`
- `RECLAIM_REFERENCE_CLOSE`: count `3`, matured `3`, mean `-37.30722`, win_rate `33.333333`, pf `0.450107`, research_candidate `False`
- `MAX_SPREAD_SLIPPAGE_PROXY_BPS`: count `1`, matured `1`, mean `239.355426`, win_rate `100.0`, pf `999.0`, research_candidate `False`
- `MIN_SWEEP_DEPTH_BPS`: count `1`, matured `1`, mean `-20.759354`, win_rate `0.0`, pf `0.0`, research_candidate `False`
- `RECLAIM_REFERENCE_CLOSE + MAX_COMPRESSION_RATIO_REFERENCE`: count `1`, matured `1`, mean `-146.868251`, win_rate `0.0`, pf `0.0`, research_candidate `False`

## Recommendation

Review near-miss outcome by gate combo only as no-order counterfactual research. Do not relax parameters, train, reload, paper trade, live trade, or send orders without a separate accepted research gate.
