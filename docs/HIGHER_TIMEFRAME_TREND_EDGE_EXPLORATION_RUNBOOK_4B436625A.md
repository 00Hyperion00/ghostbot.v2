# 4B.4.3.6.6.25A Higher Timeframe Trend Edge Exploration Runbook

## Purpose

This patch opens the first post-no-go research cycle for `HYP-001 — Higher timeframe trend following`.
It searches for positive net edge across higher timeframes, symbols, and trend/breakout strategy families.

## Guardrails

- Public market data GET requests only.
- No config mutation.
- No model training.
- No model reload.
- No order actions.
- No paper trading start.
- No live trading permission.
- Backtest PASS is not paper permission.
- Paper PASS is not live permission.

## Default exploration

```powershell
python tools/run_higher_timeframe_trend_edge_exploration_4B436625A.py `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --intervals 30m,1h,4h `
  --days 180 `
  --base-url https://api.binance.com `
  --review-ok
```

Longer horizon:

```powershell
python tools/run_higher_timeframe_trend_edge_exploration_4B436625A.py `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --intervals 30m,1h,4h `
  --days 365 `
  --base-url https://api.binance.com `
  --review-ok
```

Local CSV:

```powershell
python tools/run_higher_timeframe_trend_edge_exploration_4B436625A.py `
  --input-csv data\BTCUSDT_1h.csv `
  --symbols BTCUSDT `
  --intervals 1h `
  --review-ok
```

## Strategy families

- `ema_trend_continuation`
- `atr_breakout_volume`
- `pullback_to_vwap_in_trend`
- `volatility_compression_breakout`

## Acceptance metrics

A research candidate requires enough samples/signals, controlled coverage, balanced side distribution,
positive mean and median net edge, profit factor above floor, acceptable drawdown, OOS edge, and walk-forward stability.
A PASS only identifies a research candidate for the next controlled phase.

## No-go result

If the tool returns `BLOCK`, do not train models, promote candidates, reload models, start paper trading, or enable live trading from HYP-001.
