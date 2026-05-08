# 4B.4.3.6.6.25B Futures Funding / Open Interest Edge Exploration

## Purpose

This phase tests HYP-002: whether Binance USDⓈ-M futures public behavioural data can produce a research-grade net edge before any new model work is opened.

The tool evaluates funding rate, open-interest history, global long/short ratio, and taker buy/sell volume signals across symbol/timeframe combinations.

## Guardrails

- Observation only.
- Public futures market-data GET requests only.
- No account keys.
- No POST requests.
- No config mutation.
- No model training.
- No model reload.
- No order actions.
- Backtest PASS is not paper permission.
- Paper PASS is not live permission.

## Usage

```powershell
python tools/run_futures_funding_open_interest_edge_exploration_4B436625B.py `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --intervals 30m,1h,4h `
  --days 30 `
  --base-url https://fapi.binance.com `
  --review-ok
```

Longer exploratory run:

```powershell
python tools/run_futures_funding_open_interest_edge_exploration_4B436625B.py `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --intervals 1h,4h `
  --days 90 `
  --base-url https://fapi.binance.com `
  --review-ok
```

Local CSV:

```powershell
python tools/run_futures_funding_open_interest_edge_exploration_4B436625B.py `
  --input-csv data\BTCUSDT_1h_futures.csv `
  --symbols BTCUSDT `
  --intervals 1h `
  --review-ok
```

## Outputs

- `reports/4B436625B_futures_funding_open_interest_edge_exploration_*.json`
- `reports/4B436625B_futures_funding_open_interest_edge_exploration_*.md`

## PASS Meaning

A PASS only means a futures behavioural-data strategy is a research candidate for the next controlled phase. It does not authorize training, paper trading, live trading, promote, reload, or config mutation.

## BLOCK Meaning

A BLOCK means no tested futures funding/open-interest strategy passed the research edge gate. Move to the next pre-registered hypothesis or revise the hypothesis before coding further.

## 25B endpoint resilience note

A later hotfix clamps optional `/futures/data/*` requests to the latest 29 days because Binance exposes only the latest 30 days / 1 month for these statistics. If optional futures metrics fail with HTTP 400, the runner now records them as missing data and lets the gate decide via metric coverage / edge criteria instead of crashing.
