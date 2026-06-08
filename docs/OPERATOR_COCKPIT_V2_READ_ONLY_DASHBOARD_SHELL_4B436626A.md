# 4B.4.3.6.6.26A — Operator Cockpit V2 — Visual UX Foundation / Read-Only Dashboard Shell

This patch adds a local, layered and visually structured operator cockpit foundation for TradeBot V2.

## Scope

- Modern dark-theme dashboard shell.
- HYP-005-R1 isolated shadow audit integration.
- Scheduler state visibility for the frozen baseline task and active R1 task.
- R1 sample progress, maturity, profit factor, mean edge and win-rate summary.
- Timestamp-cluster tail-risk visibility.
- Slippage proxy warnings.
- Read-only model discovery and SHA-256 visibility.
- Latest observation table, symbol distribution and activity feed.
- Responsive layout with progressive disclosure for technical source paths.

## Safety contract

The patch is intentionally read-only.

- No config mutation.
- No scheduler mutation.
- No model reload.
- No paper-mode enable.
- No live-mode enable.
- No order action.
- No POST request to Binance.
- All POST, PUT, PATCH and DELETE calls to the dashboard server return `405 READ_ONLY_DASHBOARD_MUTATION_BLOCKED`.
- The dashboard binds to `127.0.0.1` by default.

## Run

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
powershell -ExecutionPolicy Bypass -File tools\start_operator_cockpit_v2_4B436626A.ps1
```

Open:

```text
http://127.0.0.1:8090/dashboard
```

## Operator experience

The main screen presents the operational summary first. Quant metrics, risk detail, observations and audit sources are layered below the summary rather than being placed into a single crowded panel.

The shell is designed to evolve through later dashboard packs without coupling the user interface to trading-state mutation.
