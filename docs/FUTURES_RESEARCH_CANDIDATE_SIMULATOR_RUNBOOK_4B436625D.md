# 4B.4.3.6.6.25D Futures Research Candidate Dry-Run Signal Simulator

## Purpose

25D converts the 25C robustness-confirmed futures research candidate into a dry-run signal simulator. It records a candidate specification, replays public Binance USDⓈ-M futures market data, generates dry-run signals for `funding_trend_exhaustion`, and evaluates net edge after fee/slippage assumptions.

## Safety Policy

- Uses public futures market data only.
- Uses GET requests only.
- Does not train models.
- Does not reload models.
- Does not mutate config.
- Does not start paper trading.
- Does not send orders.
- Does not enable live trading.

Backtest PASS is not paper permission.
Paper PASS is not live permission.

## Main Command

```powershell
python tools/run_futures_research_candidate_simulator_4B436625D.py `
  --input-json reports\4B436625C_futures_candidate_robustness_audit_20260508_103728.json `
  --days 90 `
  --base-url https://fapi.binance.com `
  --out-dir reports `
  --write-spec `
  --review-ok
```

## Local CSV Command

```powershell
python tools/run_futures_research_candidate_simulator_4B436625D.py `
  --input-csv data\BTCUSDT_4h_futures.csv `
  --symbol BTCUSDT `
  --interval 4h `
  --out-dir reports `
  --review-ok
```

## Gate

The simulator requires enough signals, positive mean and median net edge, acceptable profit factor, acceptable drawdown, positive OOS edge, walk-forward stability, acceptable side balance, and sufficient funding coverage.

## Outputs

- `reports/4B436625D_futures_research_candidate_simulator_*.json`
- `reports/4B436625D_futures_research_candidate_simulator_*.md`
- optional candidate spec JSON when `--write-spec` is used

## Next Step

A PASS only means the candidate may move to the next controlled research review phase. Training, paper trading, and live trading remain blocked.
