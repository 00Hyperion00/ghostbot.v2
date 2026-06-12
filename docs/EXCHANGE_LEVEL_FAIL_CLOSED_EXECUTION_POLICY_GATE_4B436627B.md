# 4B.4.3.6.6.27B — Exchange-Level Fail-Closed Execution Policy Gate

This patch adds a mandatory exchange-adapter policy gate before any signed Binance order, order-test, or cancellation request can leave the process.

## Scope

- Adds `src/tradebot/execution_policy.py`.
- Wires `BinanceSpotClient._signed_request()` to enforce the policy before API key validation and before any network call.
- Keeps read-only signed GET queries allowed.
- Blocks unknown signed non-read action classes by default.
- Does not enable paper, live demo, live real, training, reload, or any order action.

## Policy summary

| Action | dry_run | live_demo + spot_demo/testnet | live_real + spot_mainnet |
|---|---:|---:|---:|
| ENTRY_NEW_RISK | Deny | Allow | Requires armed + double confirm |
| EXIT_RISK_REDUCING | Deny | Allow | Allow |
| CANCEL_PENDING | Deny | Allow | Allow |
| ORDER_TEST | Deny | Allow | Requires armed + double confirm |
| READ_ONLY_QUERY | Allow | Allow | Allow |

## Important risk note

Live-real risk-reducing exits and pending-order cancellations are not trapped behind `live_trading_armed` and `live_real_double_confirm`; this is deliberate to avoid locking emergency risk reduction after a position or pending order already exists.
