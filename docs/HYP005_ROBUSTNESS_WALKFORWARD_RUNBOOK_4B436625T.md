# 4B.4.3.6.6.25T HYP-005 Robustness / Walk-Forward Confirmation Gate

This gate validates the HYP-005 liquidity sweep reversal candidate selected by 25S.

## Purpose

25S can identify a research-only candidate. 25T checks whether that candidate survives a stricter confirmation pass:

- recomputed signal set from fresh market data or offline CSV
- 30/60/90 day recent-window checks
- walk-forward stability
- OOS edge preservation
- top-win dependency
- dominant-symbol dependency
- wick dependency
- small-sample penalty

## Expected input

A 25S `HYP005_EXPLORATION_PASS` report, typically:

```powershell
reports\4B436625S_hyp005_liquidity_sweep_reversal_exploration_*.json
```

## Run

```powershell
python tools/run_hyp005_robustness_walkforward_4B436625T.py `
  --input-json reports\4B436625S_hyp005_liquidity_sweep_reversal_exploration_20260509_172138.json `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --interval 4h `
  --days 90 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

## Decisions

- `HYP005_ROBUSTNESS_PASS`: research-only confirmation candidate identified.
- `HYP005_ROBUSTNESS_BLOCK`: candidate failed robustness/walk-forward confirmation.

## Guardrails

- Market data access is public GET only.
- No POST requests.
- No config mutation.
- No model training.
- No model reload.
- No order actions.
- Training remains blocked.
- Paper/live remain blocked.

A PASS is not permission to train, reload, start paper trading, or enable live trading.
