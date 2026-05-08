# 4B.4.3.6.6.24O Research Restart Charter + Hypothesis Registry

## Decision Context

The previous research cycle ended with `RESEARCH_STOP_NO_GO`. The next cycle must not continue by loosening thresholds, promoting blocked models, or forcing paper trading. A new cycle can only start with a pre-registered edge hypothesis and explicit acceptance metrics.

## Non-Negotiable Guardrails

- Backtest PASS is not paper permission.
- Paper PASS is not live permission.
- Live trading remains blocked until later phases create separate live-readiness evidence.
- No tool in this phase may send orders, mutate runtime config, reload a model, or perform POST actions.
- All costs, fees, slippage, and lookahead-leakage checks must be explicit.

## Required Hypothesis Format

Each hypothesis must define:

- `hypothesis_id`
- `name`
- `market`
- `symbols`
- `timeframes`
- `strategy_family`
- `data_requirements`
- `acceptance_metrics`
- `guardrails`

Minimum acceptance metrics:

```yaml
min_net_edge_bps: 3.0
min_profit_factor: 1.15
min_trade_count: 100
max_drawdown_pct: 8.0
oos_required: true
walk_forward_required: true
fee_slippage_included: true
lookahead_leakage_tolerance: zero
```

## Default Hypothesis Backlog

1. Higher timeframe trend following
2. Futures funding and open-interest edge
3. Regime-specific strategy family
4. Portfolio relative-strength rotation
5. Order-flow and volume imbalance research

## Policy

A `REGISTRY_READY` result only means a hypothesis is sufficiently specified for the next research exploration phase. It does not authorize training promotion, model reload, paper trading, or live trading.
