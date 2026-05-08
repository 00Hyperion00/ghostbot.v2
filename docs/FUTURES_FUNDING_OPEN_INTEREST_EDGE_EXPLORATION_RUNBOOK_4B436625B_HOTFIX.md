# 4B.4.3.6.6.25B endpoint resilience hotfix

This hotfix keeps the 25B futures funding/open-interest exploration tool in research-only mode and fixes public futures data endpoint fragility.

## Why

Binance `/futures/data/*` endpoints expose only the latest 30 days / 1 month of data. Requests with a `startTime` outside that retention window can return HTTP 400. The original 25B runner treated optional futures data endpoint failures as fatal.

## What changed

- Clamp `/futures/data/openInterestHist`, `/futures/data/globalLongShortAccountRatio`, and `/futures/data/takerlongshortRatio` requests to a conservative latest-29-day window.
- Keep OHLCV kline history at the requested lookback.
- Treat optional futures metrics endpoint failures as missing data, not as a process crash.
- Preserve public GET-only behavior.
- Preserve no config mutation, no reload, no orders, no paper/live permission.

## Validation

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_futures_funding_endpoint_resilience_4B436625B.py tests/test_futures_funding_open_interest_edge_exploration_4B436625B.py
```

Expected: all tests pass.
