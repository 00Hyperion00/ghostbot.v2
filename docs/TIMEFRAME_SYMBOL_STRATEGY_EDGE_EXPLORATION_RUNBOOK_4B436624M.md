# 4B.4.3.6.6.24M Timeframe / Symbol / Strategy Edge Exploration

This patch adds a GET-only research tool for exploring whether any symbol, timeframe, and simple baseline strategy family shows positive net edge before more ML work is attempted.

## Guardrails

- Does not mutate config.
- Does not train models.
- Does not reload models.
- Does not start paper trading.
- Does not send orders.
- A PASS only means a research candidate exists; paper/live trading remains blocked.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436624M_timeframe_symbol_strategy_edge_exploration_patch.zip" -DestinationPath . -Force
python tools/apply_4B436624M_timeframe_symbol_strategy_edge_exploration.py
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_timeframe_symbol_strategy_edge_exploration_4B436624M.py
```

## Run public market exploration

```powershell
python tools/run_timeframe_symbol_strategy_edge_exploration_4B436624M.py `
  --symbols ETHUSDT,BTCUSDT,SOLUSDT,BNBUSDT `
  --intervals 1m,3m,5m,15m `
  --days 30 `
  --base-url https://api.binance.com `
  --review-ok
```

## Output

The tool writes:

- `reports/4B436624M_timeframe_symbol_strategy_edge_exploration_*.json`
- `reports/4B436624M_timeframe_symbol_strategy_edge_exploration_*.md`

## Interpretation

- `PASS`: a public-market-data research candidate exists. It is not a training, paper, or live approval.
- `BLOCK`: no tested combination showed enough positive net edge after cost.

Real live trading remains blocked regardless of this report.
