# 4B.4.3.6.6.27A — Binance REST / WebSocket Environment Consistency Router

## Scope

This fail-closed overlay removes the mainnet-only market WebSocket URL from the Binance spot client and maps REST + WebSocket market-stream endpoints from one `market_type` profile.

## Profiles

| market_type | REST origin | Combined market WebSocket base |
|---|---|---|
| `spot_mainnet` | `https://api.binance.com` | `wss://stream.binance.com:9443/stream` |
| `spot_demo` | `https://demo-api.binance.com` | `wss://demo-stream.binance.com:9443/stream` |
| `spot_testnet` | `https://testnet.binance.vision` | `wss://stream.testnet.binance.vision:9443/stream` |

## Fail-closed behavior

A configured REST host that does not belong to the selected `market_type` raises:

```text
BINANCE_REST_WS_ENVIRONMENT_MISMATCH
```

The client fails before opening an HTTP or WebSocket connection. The config-safety snapshot also marks the profile `critical` and `safe_to_trade=false`.

## Safety

- No scheduler configuration mutation.
- No runtime config rewrite.
- No paper/live enablement.
- No order action.
