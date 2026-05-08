# 4B.4.3.6.6.24O Research Restart Charter + Hypothesis Registry

- contract_version: `4B.4.3.6.6.24O`
- decision: **REGISTRY_READY**
- previous_decision: `RESEARCH_STOP_NO_GO`
- hypothesis_count: `5`
- valid_hypothesis_count: `5`
- selected_next_hypothesis_id: `HYP-001`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- recommendation: Research restart registry is ready. Select exactly one pre-registered hypothesis for the next exploration phase; paper/live remain blocked until future acceptance gates pass.

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- paper_allowed: `False`
- live_real_allowed: `False`

## Hypotheses

| id | decision | priority | name | market | timeframes | strategy_family | reasons |
|---|---|---:|---|---|---|---|---|
| HYP-001 | READY_FOR_RESEARCH_DESIGN | 1 | Higher timeframe trend following | spot | 30m, 1h, 4h | trend_following_volatility_regime |  |
| HYP-002 | READY_FOR_RESEARCH_DESIGN | 2 | Futures funding and open-interest edge | futures | 15m, 1h, 4h | funding_open_interest_sentiment |  |
| HYP-003 | READY_FOR_RESEARCH_DESIGN | 3 | Regime-specific strategy family | spot | 15m, 30m, 1h | trend_range_volatility_router |  |
| HYP-004 | READY_FOR_RESEARCH_DESIGN | 4 | Portfolio relative-strength rotation | spot | 1h, 4h | multi_symbol_relative_strength_rotation |  |
| HYP-005 | READY_FOR_RESEARCH_DESIGN | 5 | Order-flow and volume imbalance research | spot_or_futures | 1m, 3m, 5m, 15m | order_flow_volume_imbalance |  |

## Next Hypothesis Backlog

- higher_timeframe_trend_following
- futures_funding_open_interest_edge
- regime_specific_strategy_family
- portfolio_relative_strength_rotation
- order_flow_volume_imbalance_research

## Policy

This registry does not start paper trading, enable live trading, reload models, mutate config, or send orders. A REGISTRY_READY decision only permits selecting one pre-registered research hypothesis for the next exploration phase.
