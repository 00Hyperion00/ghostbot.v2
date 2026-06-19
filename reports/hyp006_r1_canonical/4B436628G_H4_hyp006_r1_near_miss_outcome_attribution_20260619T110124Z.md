# 4B.4.3.6.6.28G-H4 HYP-006 Near-Miss Outcome Attribution

- decision: `HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_READY`
- branch_id: `HYP-006-R1`
- read_only: `True`
- counterfactual_research_only: `True`
- attributed_near_miss_event_count: `100`
- matured_near_miss_event_count: `100`
- near_miss_mean_return_bps: `85.53325`
- near_miss_win_rate_pct: `52.0`
- trigger_benchmark_mean_return_bps: `108.911085`
- trigger_benchmark_win_rate_pct: `50.0`
- approved_for_parameter_relaxation_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`

## Gate combo outcome summary

- `MAX_COMPRESSION_RATIO_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS`: count `17`, matured `17`, mean `160.48751`, win_rate `70.588235`, pf `2.951483`, research_candidate `True`
- `MAX_COMPRESSION_RATIO_REFERENCE`: count `12`, matured `12`, mean `166.61927`, win_rate `58.333333`, pf `7.046963`, research_candidate `True`
- `MIN_WICK_PCT_REFERENCE + MAX_COMPRESSION_RATIO_REFERENCE`: count `9`, matured `9`, mean `258.042239`, win_rate `77.777778`, pf `18.702614`, research_candidate `True`
- `MIN_SWEEP_DEPTH_BPS + MIN_WICK_PCT_REFERENCE`: count `7`, matured `7`, mean `88.17779`, win_rate `57.142857`, pf `1.78504`, research_candidate `True`
- `MIN_WICK_PCT_REFERENCE`: count `4`, matured `4`, mean `228.746244`, win_rate `75.0`, pf `18.49582`, research_candidate `True`
- `RECLAIM_REFERENCE_CLOSE + MIN_WICK_PCT_REFERENCE`: count `37`, matured `37`, mean `-13.143897`, win_rate `35.135135`, pf `0.86865`, research_candidate `False`
- `MIN_SWEEP_DEPTH_BPS + MAX_COMPRESSION_RATIO_REFERENCE`: count `4`, matured `4`, mean `92.112111`, win_rate `50.0`, pf `5.102721`, research_candidate `False`
- `RECLAIM_REFERENCE_CLOSE + MAX_SPREAD_SLIPPAGE_PROXY_BPS`: count `3`, matured `3`, mean `-9.312926`, win_rate `33.333333`, pf `0.415166`, research_candidate `False`
- `RECLAIM_REFERENCE_CLOSE`: count `3`, matured `3`, mean `-37.30722`, win_rate `33.333333`, pf `0.450107`, research_candidate `False`
- `MAX_SPREAD_SLIPPAGE_PROXY_BPS`: count `1`, matured `1`, mean `239.355426`, win_rate `100.0`, pf `999.0`, research_candidate `False`
- `MIN_WICK_PCT_REFERENCE + MAX_SPREAD_SLIPPAGE_PROXY_BPS`: count `1`, matured `1`, mean `157.004831`, win_rate `100.0`, pf `999.0`, research_candidate `False`
- `MIN_SWEEP_DEPTH_BPS`: count `1`, matured `1`, mean `-20.759354`, win_rate `0.0`, pf `0.0`, research_candidate `False`

## Recommendation

Review near-miss outcome by gate combo only as no-order counterfactual research. Do not relax parameters, train, reload, paper trade, live trade, or send orders without a separate accepted research gate.
