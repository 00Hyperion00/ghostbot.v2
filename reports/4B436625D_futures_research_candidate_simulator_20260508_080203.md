# 4B.4.3.6.6.25D Futures Research Candidate Dry-Run Signal Simulator

- contract_version: `4B.4.3.6.6.25D`
- decision: **BLOCK**
- source: `binance-futures:BTCUSDT:4h:90d`
- selected: `BTCUSDT` `4h` `funding_trend_exhaustion`
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
| signal_count | `27` |
| signal_coverage_pct | `5.0` |
| mean_net_edge_bps | `16.295166` |
| median_net_edge_bps | `-23.26973` |
| win_rate_pct | `48.148148` |
| profit_factor | `1.18424` |
| max_drawdown_pct | `6.399669` |
| oos_mean_net_edge_bps | `25.542525` |
| walk_forward_positive_rate_pct | `25.0` |
| buy_count | `11` |
| sell_count | `16` |
| dominant_action_pct | `59.259259` |
| top_trade_edge_share_pct | `19.598641` |
| funding_coverage_pct | `100.0` |
| open_interest_coverage_pct | `32.222222` |
| long_short_coverage_pct | `32.222222` |
| taker_coverage_pct | `32.407407` |
| round_trip_cost_bps | `20.0` |

## Decision

- reason_codes: `['NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED', 'DRY_RUN_SIGNAL_COUNT_LOW', 'DRY_RUN_MEDIAN_EDGE_LOW', 'DRY_RUN_WALK_FORWARD_STABILITY_LOW']`
- warnings: `['DRY_RUN_SIGNAL_COUNT_NEAR_FLOOR']`

## First Trades

| # | entry_time | exit_time | side | net_edge_bps | reason |
|---:|---|---|---|---:|---|
| 1 | 2026-02-23 12:00:00+00:00 | 2026-02-24 00:00:00+00:00 | BUY | -412.967895 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 2 | 2026-02-27 12:00:00+00:00 | 2026-02-28 00:00:00+00:00 | BUY | -69.959149 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 3 | 2026-02-28 12:00:00+00:00 | 2026-03-01 00:00:00+00:00 | BUY | 554.248085 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 4 | 2026-03-01 04:00:00+00:00 | 2026-03-01 16:00:00+00:00 | BUY | -249.537546 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 5 | 2026-03-02 16:00:00+00:00 | 2026-03-03 04:00:00+00:00 | BUY | -157.619393 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 6 | 2026-03-04 20:00:00+00:00 | 2026-03-05 08:00:00+00:00 | SELL | 75.188522 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 7 | 2026-03-05 12:00:00+00:00 | 2026-03-06 00:00:00+00:00 | SELL | 231.728869 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 8 | 2026-03-09 00:00:00+00:00 | 2026-03-09 12:00:00+00:00 | BUY | 419.52844 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 9 | 2026-03-09 16:00:00+00:00 | 2026-03-10 04:00:00+00:00 | BUY | 204.065992 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 10 | 2026-03-13 16:00:00+00:00 | 2026-03-14 04:00:00+00:00 | SELL | 151.935694 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 11 | 2026-03-16 00:00:00+00:00 | 2026-03-16 12:00:00+00:00 | SELL | -83.397583 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 12 | 2026-03-16 16:00:00+00:00 | 2026-03-17 04:00:00+00:00 | SELL | -152.78227 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 13 | 2026-03-23 00:00:00+00:00 | 2026-03-23 12:00:00+00:00 | BUY | 316.352124 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 14 | 2026-03-27 12:00:00+00:00 | 2026-03-28 00:00:00+00:00 | BUY | -90.728572 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 15 | 2026-03-28 16:00:00+00:00 | 2026-03-29 04:00:00+00:00 | BUY | -72.237603 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 16 | 2026-04-01 08:00:00+00:00 | 2026-04-01 20:00:00+00:00 | BUY | -102.357517 | NEGATIVE_FUNDING_TREND_EXHAUSTION |
| 17 | 2026-04-06 12:00:00+00:00 | 2026-04-07 00:00:00+00:00 | SELL | 100.315879 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 18 | 2026-04-07 12:00:00+00:00 | 2026-04-08 00:00:00+00:00 | SELL | -451.689325 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 19 | 2026-04-08 04:00:00+00:00 | 2026-04-08 16:00:00+00:00 | SELL | -23.26973 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 20 | 2026-04-09 16:00:00+00:00 | 2026-04-10 04:00:00+00:00 | SELL | 69.698785 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 21 | 2026-04-14 16:00:00+00:00 | 2026-04-15 04:00:00+00:00 | SELL | 187.657693 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 22 | 2026-04-17 12:00:00+00:00 | 2026-04-18 00:00:00+00:00 | SELL | -208.265881 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 23 | 2026-04-22 16:00:00+00:00 | 2026-04-23 04:00:00+00:00 | SELL | 134.630002 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 24 | 2026-04-27 00:00:00+00:00 | 2026-04-27 12:00:00+00:00 | SELL | 215.885538 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 25 | 2026-04-29 04:00:00+00:00 | 2026-04-29 16:00:00+00:00 | SELL | 166.756796 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 26 | 2026-04-30 00:00:00+00:00 | 2026-04-30 12:00:00+00:00 | SELL | -108.858203 | POSITIVE_FUNDING_TREND_EXHAUSTION |
| 27 | 2026-05-04 00:00:00+00:00 | 2026-05-04 12:00:00+00:00 | SELL | -204.352278 | POSITIVE_FUNDING_TREND_EXHAUSTION |

## Policy

This tool uses public futures market data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a research candidate for the next controlled phase; paper/live trading remains blocked.
