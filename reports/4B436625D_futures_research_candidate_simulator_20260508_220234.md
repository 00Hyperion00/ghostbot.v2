# 4B.4.3.6.6.25D Futures Research Candidate Dry-Run Signal Simulator

- contract_version: `4B.4.3.6.6.25D`
- decision: **BLOCK**
- source: `binance-futures:ETHUSDT:4h:90d`
- selected: `ETHUSDT` `4h` `funding_trend_exhaustion`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- recommendation: No futures dry-run research candidate passed. Do not train, reload, start paper trading, or enable live trading. Revisit the futures hypothesis or robustness inputs.

## Guardrails

- observation_only: `True`
- get_only_public_futures_data: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- backtest_pass_is_not_paper_permission: `True`
- paper_pass_is_not_live_permission: `True`

## Metrics

| metric | value |
|---|---:|
| rows | `540` |
| signal_count | `36` |
| signal_coverage_pct | `6.666667` |
| mean_net_edge_bps | `69.5964` |
| median_net_edge_bps | `96.251131` |
| win_rate_pct | `72.222222` |
| profit_factor | `1.907343` |
| max_drawdown_pct | `7.843292` |
| oos_mean_net_edge_bps | `-17.81631` |
| walk_forward_positive_rate_pct | `75.0` |
| buy_count | `17` |
| sell_count | `19` |
| dominant_action_pct | `52.777778` |
| top_trade_edge_share_pct | `11.178734` |
| funding_coverage_pct | `100.0` |
| open_interest_coverage_pct | `32.222222` |
| long_short_coverage_pct | `32.222222` |
| taker_coverage_pct | `32.407407` |
| round_trip_cost_bps | `20.0` |

## Decision

- reason_codes: `['NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'DRY_RUN_OOS_EDGE_LOW']`
- warnings: `['DRY_RUN_SIGNAL_COUNT_NEAR_FLOOR']`

## First Trades

| # | entry_time | exit_time | side | net_edge_bps | reason |
|---:|---|---|---|---:|---|
| 1 | 2026-02-20 20:00:00+00:00 | 2026-02-21 08:00:00+00:00 | BUY | 48.062907 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 2 | 2026-02-23 12:00:00+00:00 | 2026-02-24 00:00:00+00:00 | BUY | -455.959047 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 3 | 2026-02-26 08:00:00+00:00 | 2026-02-26 20:00:00+00:00 | SELL | 105.603535 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 4 | 2026-02-27 04:00:00+00:00 | 2026-02-27 16:00:00+00:00 | SELL | 588.761152 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 5 | 2026-02-28 08:00:00+00:00 | 2026-02-28 20:00:00+00:00 | BUY | 505.954636 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 6 | 2026-03-01 00:00:00+00:00 | 2026-03-01 12:00:00+00:00 | BUY | 126.831137 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 7 | 2026-03-01 16:00:00+00:00 | 2026-03-02 04:00:00+00:00 | SELL | 241.255835 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 8 | 2026-03-02 12:00:00+00:00 | 2026-03-03 00:00:00+00:00 | BUY | 294.094167 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 9 | 2026-03-04 20:00:00+00:00 | 2026-03-05 08:00:00+00:00 | SELL | 162.451401 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 10 | 2026-03-08 16:00:00+00:00 | 2026-03-09 04:00:00+00:00 | BUY | 190.555043 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 11 | 2026-03-09 08:00:00+00:00 | 2026-03-09 20:00:00+00:00 | BUY | 27.304453 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 12 | 2026-03-10 12:00:00+00:00 | 2026-03-11 00:00:00+00:00 | SELL | 176.479957 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 13 | 2026-03-16 00:00:00+00:00 | 2026-03-16 12:00:00+00:00 | SELL | -454.81056 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 14 | 2026-03-16 16:00:00+00:00 | 2026-03-17 04:00:00+00:00 | SELL | -259.129382 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 15 | 2026-03-17 08:00:00+00:00 | 2026-03-17 20:00:00+00:00 | SELL | 24.224967 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 16 | 2026-03-23 00:00:00+00:00 | 2026-03-23 12:00:00+00:00 | BUY | 343.833871 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 17 | 2026-03-25 00:00:00+00:00 | 2026-03-25 12:00:00+00:00 | BUY | 9.55505 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 18 | 2026-03-26 08:00:00+00:00 | 2026-03-26 20:00:00+00:00 | SELL | 277.734597 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 19 | 2026-03-27 00:00:00+00:00 | 2026-03-27 12:00:00+00:00 | BUY | -355.376218 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 20 | 2026-03-27 16:00:00+00:00 | 2026-03-28 04:00:00+00:00 | BUY | 59.543342 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 21 | 2026-03-28 16:00:00+00:00 | 2026-03-29 04:00:00+00:00 | BUY | -122.675486 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 22 | 2026-03-30 00:00:00+00:00 | 2026-03-30 12:00:00+00:00 | BUY | 433.502735 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 23 | 2026-04-01 20:00:00+00:00 | 2026-04-02 08:00:00+00:00 | SELL | 485.595141 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 24 | 2026-04-02 16:00:00+00:00 | 2026-04-03 04:00:00+00:00 | BUY | 11.722898 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 25 | 2026-04-06 00:00:00+00:00 | 2026-04-06 12:00:00+00:00 | BUY | 236.333675 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 26 | 2026-04-06 16:00:00+00:00 | 2026-04-07 04:00:00+00:00 | SELL | 259.324961 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 27 | 2026-04-08 04:00:00+00:00 | 2026-04-08 16:00:00+00:00 | SELL | 86.898728 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 28 | 2026-04-08 20:00:00+00:00 | 2026-04-09 08:00:00+00:00 | SELL | 120.180995 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 29 | 2026-04-12 04:00:00+00:00 | 2026-04-12 16:00:00+00:00 | SELL | 49.914268 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 30 | 2026-04-13 16:00:00+00:00 | 2026-04-14 04:00:00+00:00 | SELL | -784.329191 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 31 | 2026-04-14 12:00:00+00:00 | 2026-04-15 00:00:00+00:00 | SELL | 171.856325 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 32 | 2026-04-22 16:00:00+00:00 | 2026-04-23 04:00:00+00:00 | SELL | 229.220665 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 33 | 2026-04-28 08:00:00+00:00 | 2026-04-28 20:00:00+00:00 | BUY | -11.821561 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 34 | 2026-04-30 08:00:00+00:00 | 2026-04-30 20:00:00+00:00 | BUY | -31.111111 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 35 | 2026-05-04 00:00:00+00:00 | 2026-05-04 12:00:00+00:00 | SELL | -136.080235 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 36 | 2026-05-04 16:00:00+00:00 | 2026-05-05 04:00:00+00:00 | SELL | -150.033253 | POSITIVE_FUNDING_TREND_EXHAUSTION |

## Policy

This tool uses public futures market data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a research candidate for the next controlled phase; paper/live trading remains blocked.
