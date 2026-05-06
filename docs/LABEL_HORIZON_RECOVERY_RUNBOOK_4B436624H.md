# 4B.4.3.6.6.24H Label Horizon / Target Engineering Recovery Runbook

## Purpose

24E/24F showed that BUY/SELL raw probabilities are too close and safe threshold relaxation does not produce a paper candidate. 24H evaluates label horizon and ATR target policies before another retrain attempt.

## Guardrails

This tool is observation-only.

- Uses public market data or local OHLCV input.
- Does not mutate config.
- Does not retrain automatically.
- Does not reload models.
- Does not submit orders.
- Does not approve paper or real-live trading.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436624H_label_horizon_recovery_patch.zip" -DestinationPath . -Force
python tools/apply_4B436624H_label_horizon_recovery.py
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_label_horizon_recovery_4B436624H.py
```

## Run with Binance public klines

```powershell
python tools/run_label_horizon_recovery_4B436624H.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --review-ok
```

## Run with local OHLCV CSV

```powershell
python tools/run_label_horizon_recovery_4B436624H.py `
  --input-csv data\ETHUSDT_1m.csv `
  --review-ok
```

## Interpreting results

- `PASS`: A label policy candidate is safe enough for a controlled retrain sweep. It is not a paper/live approval.
- `BLOCK`: No label policy candidate passed. Do not retrain/promote based on the current label setup.

Important blockers:

- `TARGET_ACTION_COVERAGE_HIGH`: too many labels are BUY/SELL.
- `TARGET_ACTION_COVERAGE_LOW`: too few action labels.
- `TARGET_ACTION_SIDE_IMBALANCE_HIGH`: BUY/SELL targets are one-sided.
- `FORWARD_RETURN_SEPARATION_LOW`: BUY and SELL labels do not separate future returns enough.
- `TARGET_DIRECTIONAL_ENTROPY_LOW`: directional labels are too concentrated.

## Next step

If 24H PASSes, use the selected policy only as an input to a controlled retrain candidate sweep. If it BLOCKs, revisit horizon, ATR multiplier, cost assumptions, and features before touching thresholds.
