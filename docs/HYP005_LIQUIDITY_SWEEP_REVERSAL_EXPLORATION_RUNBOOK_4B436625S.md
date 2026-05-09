# 4B.4.3.6.6.25S HYP-005 Liquidity Sweep Reversal Exploration Gate

This patch opens the first research-only exploration gate for HYP-005: liquidity sweep reversal with volatility compression filter.

## Purpose

The gate evaluates whether stop-hunt / liquidity sweep reversal patterns have enough edge to become a research candidate. It checks long sweep reversals, short sweep reversals, compression sweep reversals, and a diagnostic fakeout probe.

## Strategy Families

- `long_liquidity_sweep_reversal`
- `short_liquidity_sweep_reversal`
- `compression_sweep_reversal`
- `compression_breakout_fakeout_probe` — diagnostic only, never approvable

## Metrics

- signal_count
- mean_net_edge_bps
- median_net_edge_bps
- profit_factor
- win_rate_pct
- oos_mean_net_edge_bps
- walk_forward_positive_rate_pct
- dominant_symbol_pct
- top_win_dependency_pct
- wick_dependency_pct
- symbols_traded

## Guardrails

- Training remains blocked.
- Paper/live remain blocked.
- No config mutation is performed.
- No model is trained or reloaded.
- No orders are sent.
- Only public market data GET requests are used when live data is fetched.

Backtest PASS is not paper permission. Paper PASS is not live permission.

## Run

```powershell
python tools/run_hyp005_liquidity_sweep_reversal_exploration_4B436625S.py `
  --input-json reports\4B436625R_research_backlog_after_hyp004_closure_20260509_164216.json `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --interval 4h `
  --days 90 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

## Output

- `reports/4B436625S_hyp005_liquidity_sweep_reversal_exploration_*.json`
- `reports/4B436625S_hyp005_liquidity_sweep_reversal_exploration_*.md`

A PASS only identifies a research candidate. It does not approve training, paper trading, or live trading.
