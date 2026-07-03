# 4B.4.3.6.6.37I — Fee / Slippage Baseline

This patch closes P0-8 by adding a static no-submit execution-cost baseline.

## Baseline

- Maker fee baseline: 2.0 bps
- Taker fee baseline: 5.0 bps
- Slippage baseline: 5.0 bps per side
- Max slippage guard: 15.0 bps
- Break-even cost floor: entry taker fee + exit taker fee + entry slippage + exit slippage = 20.0 bps

These defaults are conservative planning values. They are not exchange-account-tier evidence and do not authorize real execution.
Before any future paper/live transition, fee rates must be reconciled with operator-approved exchange/account configuration.

## No-submit restrictions

37I does not:

- query Binance or any exchange API
- submit orders
- read private account tier data
- query live market depth/order books
- mutate runtime route/config loaders
- open paper/live transition

## Evidence

The run tool writes:

- `4B436637I_fee_slippage_baseline_*_ready|not_ready.json`
- `4B436637I_fee_slippage_baseline_*.json`
- `4B436637I_fee_slippage_probe_*.json`
- `4B436637I_p0_gap_closure_delta_*.json`
- `4B436637I_no_submit_p0_8_hardening_gate_*.json`
