# HYP-005 Shadow Observation Quality / Slippage Risk Audit Deduplication + Recommendation Message Consistency Hotfix

- contract_version: `4B.4.3.6.6.25AB-H2`
- hotfix_version: `4B.4.3.6.6.25AB-H2`
- decision: `HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED`
- generated_at_utc: `2026-05-23T20:11:32Z`
- raw_observation_count: `1026`
- unique_observation_count: `20`
- duplicate_removed_count: `1006`
- shadow_observation_count: `20`
- shadow_sample_target: `30`
- progress_pct: `66.666667`
- matured_forward_return_count: `14`
- maturity_pending_count: `6`
- true_missing_required_fields_pct: `1.0`
- mean_forward_edge_bps: `-29.455219`
- median_forward_edge_bps: `-8.611481`
- profit_factor: `0.561361`
- win_rate_pct: `42.857143`
- max_slippage_proxy_bps: `15.634462`
- high_slippage_count: `2`

## Guardrail Decision

No training, reload, paper trading, live trading, POST requests, or order actions are approved by this audit.

## Reason Codes

- `MATURED_MEAN_FORWARD_EDGE_NEGATIVE`
- `MATURED_PROFIT_FACTOR_LOW`
- `MISSING_FINAL_RETURN_CLASSIFIED_AS_MATURITY_PENDING`
- `NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED`
- `OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED`
- `OBSERVATION_DUPLICATES_REMOVED`
- `RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED`
- `SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET`
- `SHADOW_SLIPPAGE_PROXY_HIGH`

## Warnings

- `MATURED_MEAN_FORWARD_EDGE_NEGATIVE`
- `MATURED_PROFIT_FACTOR_LOW`
- `MATURITY_PENDING_FORWARD_RETURNS_PRESENT`
- `OBSERVATION_DUPLICATES_REMOVED_FROM_QUALITY_METRICS`
- `SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET`
- `SHADOW_SLIPPAGE_PROXY_HIGH`

## Per-Symbol Quality

- ADAUSDT: count=1, matured=1, pending=0, mean_edge=59.031877, pf=999.0, max_slip=4.840614, flags=
- AVAXUSDT: count=3, matured=3, pending=0, mean_edge=-61.009818, pf=0.0, max_slip=12.717391, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- BNBUSDT: count=1, matured=1, pending=0, mean_edge=25.551141, pf=999.0, max_slip=3.290488, flags=
- BTCUSDT: count=1, matured=0, pending=1, mean_edge=None, pf=None, max_slip=1.763543, flags=SYMBOL_MATURITY_PENDING_PRESENT
- DOGEUSDT: count=4, matured=3, pending=1, mean_edge=-113.326316, pf=0.32836, max_slip=15.634462, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_MATURITY_PENDING_PRESENT
- ETHUSDT: count=2, matured=1, pending=1, mean_edge=-17.222962, pf=0.0, max_slip=7.236468, flags=SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_MATURITY_PENDING_PRESENT
- LINKUSDT: count=2, matured=1, pending=1, mean_edge=52.576236, pf=999.0, max_slip=7.255521, flags=SYMBOL_MATURITY_PENDING_PRESENT
- LTCUSDT: count=1, matured=1, pending=0, mean_edge=76.165707, pf=999.0, max_slip=4.012632, flags=
- SOLUSDT: count=1, matured=0, pending=1, mean_edge=None, pf=None, max_slip=3.038488, flags=SYMBOL_MATURITY_PENDING_PRESENT
- XRPUSDT: count=4, matured=3, pending=1, mean_edge=-28.488889, pf=0.63425, max_slip=11.729452, flags=SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_MATURITY_PENDING_PRESENT

## Recommendation

HYP-005 shadow quality audit is deduped and review-required/collection-only with 20 unique shadow observations. Continue no-order shadow collection; do not train, reload, paper trade, live trade, or send orders. Review maturity-pending and slippage flags before any future transition gate.
