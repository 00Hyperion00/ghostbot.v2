# 4B.4.3.6.6.27C-H1 — Binance Demo Authenticated No-Order Preflight Probe

Explicitly approved, authenticated Binance Demo runtime verification without real order submission.

Allowed request paths:
- `GET /api/v3/time`
- `GET /api/v3/exchangeInfo`
- `GET /api/v3/ticker/price`
- `GET /api/v3/openOrders`
- `POST /api/v3/order/test`

Forbidden request path:
- `POST /api/v3/order`

Required profile:
- `market_type: spot_demo`
- `execution_mode: live_demo`
- `base_url: https://demo-api.binance.com`

Evidence JSON is written under `reports/execution_safety`. API keys, secrets, signatures and signed query strings are never exported.
