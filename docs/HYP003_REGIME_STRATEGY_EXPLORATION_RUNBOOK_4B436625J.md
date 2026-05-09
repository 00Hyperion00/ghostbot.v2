# 4B.4.3.6.6.25J HYP-003 Regime-Specific Strategy Family Exploration Gate

## Purpose

25I selected HYP-003 as the next research-only hypothesis after HYP-002 was closed no-go. 25J starts the HYP-003 exploration chain by testing regime-specific strategy families across market regimes.

## Strategy Families

- `volatility_expansion_breakout`
- `trend_pullback_continuation`
- `range_mean_reversion`
- `low_vol_breakout_probe` diagnostic only

## Regimes

- `high_vol_trend`
- `trend`
- `range`
- `low_vol`

## Guardrails

- Training remains blocked.
- Paper/live remain blocked.
- No model reload is performed.
- No config mutation is performed.
- No orders are sent.
- Public market data GET requests only.

Backtest PASS is not paper permission. Paper PASS is not live permission.

## Run with 25I report

```powershell
python tools/run_hyp003_regime_strategy_exploration_4B436625J.py `
  --input-json reports\4B436625I_research_backlog_advancement_20260509_135115.json `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 1h,4h `
  --days 90 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

## Offline CSV run

```powershell
python tools/run_hyp003_regime_strategy_exploration_4B436625J.py `
  --input-json reports\4B436625I_research_backlog_advancement_20260509_135115.json `
  --input-csv BTCUSDT:1h:data\BTCUSDT_1h.csv `
  --out-dir reports `
  --review-ok
```

## Output

- `reports/4B436625J_hyp003_regime_strategy_exploration_*.json`
- `reports/4B436625J_hyp003_regime_strategy_exploration_*.md`

## Interpretation

`HYP003_EXPLORATION_PASS` means a research-only candidate was found and must go to a later robustness gate. It does not authorize training, paper trading, live trading, model reload, or orders.
