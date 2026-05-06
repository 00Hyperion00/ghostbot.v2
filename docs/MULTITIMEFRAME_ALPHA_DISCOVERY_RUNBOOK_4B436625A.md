# 4B.4.3.6.6.25A Multi-Timeframe Alpha Discovery / Research Reset

This phase opens a research-reset lane after the 1m stack failed cost-aware, two-stage, and regime-aware edge gates.

The tool is observation-only. It fetches public market data with GET requests, evaluates multi-timeframe cost-aware label policies, and writes reports. It never mutates config, retrains production models, reloads models, starts paper trading, sends orders, or approves real-live trading.

## Typical Commands

```powershell
python tools/run_multitimeframe_alpha_discovery_4B436625A.py `
  --symbol ETHUSDT `
  --intervals 5m,15m,1h `
  --days 180 `
  --base-url https://api.binance.com `
  --review-ok
```

Use a local CSV for fast iteration:

```powershell
python tools/run_multitimeframe_alpha_discovery_4B436625A.py `
  --input-csv data\ETHUSDT_15m.csv `
  --input-interval 15m `
  --review-ok
```

## Interpretation

A PASS only identifies an offline training/research candidate. Paper and live trading remain blocked. A BLOCK means no tested multi-timeframe alpha candidate produced enough cost-aware edge and label balance for the next research sweep.
