# 4B.4.3.6.6.32B-H1 Operator Cockpit Unified Desktop Sync

This patch consolidates the operator workflow into one desktop launcher and one Tkinter-based cockpit screen.

## Single entrypoint

- `start_tradebot_v2_operator_cockpit.bat`
- `TradeBot V2 Operator Cockpit.bat`

Legacy launchers are no longer independent execution paths:

- `run_dashboard.bat`
- `start_dashboard.bat`
- `start_tradebot.bat`

They are backed up under `_legacy_launchers/4B.4.3.6.6.32B-H1/` and replaced with redirect wrappers to the unified cockpit.

## Risk contract

- No Binance submit.
- No exchange order creation.
- No second micro-canary order approval.
- 32B remains submit-request evidence only.
- Any real submit still requires a separate 32C phase.

## Cockpit sections

- Overview cards
- Risk caps / evidence chain
- Second micro-canary candidate qty and notional
- Shadow/no-order collection health
- Scheduler log tail
- Local actions: refresh, write snapshot, open reports, start no-order shadow task
