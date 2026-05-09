# 4B.4.3.6.6.25K HYP-003 Robustness / Walk-Forward Confirmation Gate

This patch validates the HYP-003 research candidate selected by 25J: `ETHUSDT 4h range_mean_reversion range`.

## Purpose

25J found an exploration candidate. 25K checks whether that candidate survives a stricter confirmation gate:

- full-sample net edge
- median edge
- profit factor
- walk-forward stability
- OOS edge
- recent-window stability
- outlier dependency
- side balance
- range-regime persistence

## Safety Policy

Training remains blocked.
Paper/live remain blocked.
Model reload remains blocked.
Order actions remain blocked.
Config mutation remains blocked.

PASS is research-only. It is not paper permission and not live permission.

## Run

```powershell
python tools/run_hyp003_robustness_walkforward_4B436625K.py `
  --input-json reports\4B436625J_hyp003_regime_strategy_exploration_20260509_110246.json `
  --days 90 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

## Local CSV Run

```powershell
python tools/run_hyp003_robustness_walkforward_4B436625K.py `
  --input-json reports\4B436625J_hyp003_regime_strategy_exploration_20260509_110246.json `
  --input-csv data\ETHUSDT_4h_90d.csv `
  --out-dir reports `
  --review-ok
```

## Expected Outputs

- `reports/4B436625K_hyp003_robustness_walkforward_confirmation_*.json`
- `reports/4B436625K_hyp003_robustness_walkforward_confirmation_*.md`

## Next Gate

If 25K passes, move to a research-only candidate specification / shadow-planning gate. Do not train, reload, paper trade, or enable live trading.
