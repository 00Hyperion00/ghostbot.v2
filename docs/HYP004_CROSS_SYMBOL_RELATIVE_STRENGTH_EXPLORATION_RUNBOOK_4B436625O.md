# 4B.4.3.6.6.25O HYP-004 Cross-Symbol Relative Strength Exploration Gate

This patch opens the HYP-004 research-only exploration gate after 25N selected `Cross-symbol relative strength rotation`.

## Strategy Families

- `leader_long_momentum`
- `laggard_reversion`
- `leader_laggard_spread`
- `short_term_rotation_probe` diagnostic only

## Gate Metrics

- signal count
- mean net edge bps
- median net edge bps
- profit factor
- win rate
- OOS mean net edge bps
- walk-forward positive rate
- dominant symbol dependency
- top-win dependency
- traded symbol count

## Guardrails

- Training remains blocked.
- Paper/live remain blocked.
- No model reload is performed.
- No config mutation is performed.
- No order actions are performed.
- Only public market data GET is used when online data is requested.

## Run

Use the latest 25N report:

```powershell
python tools/run_hyp004_cross_symbol_relative_strength_exploration_4B436625O.py `
  --input-json reports\4B436625N_research_backlog_after_hyp003_closure_20260509_152741.json `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --interval 4h `
  --days 90 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

Offline CSV mode:

```powershell
python tools/run_hyp004_cross_symbol_relative_strength_exploration_4B436625O.py `
  --input-json reports\4B436625N_research_backlog_after_hyp003_closure_20260509_152741.json `
  --input-csv data\cross_symbol_market.csv `
  --out-dir reports `
  --review-ok
```

## Output

- `reports\4B436625O_hyp004_cross_symbol_relative_strength_exploration_*.json`
- `reports\4B436625O_hyp004_cross_symbol_relative_strength_exploration_*.md`

A PASS means research-only exploration candidate identified. It does not permit training, paper trading, live trading, reload, or order actions.
