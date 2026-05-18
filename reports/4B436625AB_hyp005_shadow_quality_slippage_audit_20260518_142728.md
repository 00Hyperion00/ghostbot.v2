# HYP-005 Shadow Observation Quality / Slippage Risk Audit

- contract_version: `4B.4.3.6.6.25AB`
- decision: `HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED`
- generated_at_utc: `2026-05-18T14:27:28Z`
- shadow_observation_count: `82`
- shadow_sample_target: `30`
- progress_pct: `273.333333`
- matured_forward_return_count: `60`
- maturity_pending_count: `22`
- true_missing_required_fields_pct: `0.243902`
- mean_forward_edge_bps: `-57.430188`
- median_forward_edge_bps: `0.0`
- profit_factor: `0.178307`
- win_rate_pct: `13.333333`
- max_slippage_proxy_bps: `15.634462`
- high_slippage_count: `8`

## Guardrail Decision

No training, reload, paper trading, live trading, POST requests, or order actions are approved by this audit.

## Reason Codes

- `LOGGER_BLOCK_EXPLAINED_BY_MATURITY_PENDING_FINAL_RETURNS`
- `MATURED_MEAN_FORWARD_EDGE_NEGATIVE`
- `MATURED_PROFIT_FACTOR_LOW`
- `MISSING_FINAL_RETURN_CLASSIFIED_AS_MATURITY_PENDING`
- `NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED`
- `SHADOW_SLIPPAGE_PROXY_HIGH`
- `SYMBOL_DOMINANCE_HIGH`

## Warnings

- `LOGGER_BLOCK_IS_MATURITY_AWARE_REVIEW_ITEM`
- `MATURED_MEAN_FORWARD_EDGE_NEGATIVE`
- `MATURED_PROFIT_FACTOR_LOW`
- `MATURITY_PENDING_FORWARD_RETURNS_PRESENT`
- `SHADOW_SLIPPAGE_PROXY_HIGH`
- `SYMBOL_DOMINANCE_HIGH`

## Per-Symbol Quality

- ADAUSDT: count=13, matured=8, pending=5, mean_edge=93.467139, pf=999.0, max_slip=4.840614, flags=SYMBOL_MATURITY_PENDING_PRESENT
- AVAXUSDT: count=56, matured=52, pending=4, mean_edge=-80.645162, pf=0.0, max_slip=12.717391, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_MATURITY_PENDING_PRESENT
- BNBUSDT: count=2, matured=0, pending=2, mean_edge=None, pf=None, max_slip=3.290488, flags=SYMBOL_MATURITY_PENDING_PRESENT
- DOGEUSDT: count=4, matured=0, pending=4, mean_edge=None, pf=None, max_slip=15.634462, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MATURITY_PENDING_PRESENT
- LINKUSDT: count=1, matured=0, pending=1, mean_edge=None, pf=None, max_slip=4.795205, flags=SYMBOL_MATURITY_PENDING_PRESENT
- LTCUSDT: count=1, matured=0, pending=1, mean_edge=None, pf=None, max_slip=4.012632, flags=SYMBOL_MATURITY_PENDING_PRESENT
- SOLUSDT: count=1, matured=0, pending=1, mean_edge=None, pf=None, max_slip=3.038488, flags=SYMBOL_MATURITY_PENDING_PRESENT
- XRPUSDT: count=4, matured=0, pending=4, mean_edge=None, pf=None, max_slip=11.729452, flags=SYMBOL_MATURITY_PENDING_PRESENT

## Recommendation

HYP-005 shadow quality audit is review-required/collection-only. Continue no-order shadow collection; do not train, reload, paper trade, live trade, or send orders. Review maturity-pending and slippage flags before any future transition gate.
