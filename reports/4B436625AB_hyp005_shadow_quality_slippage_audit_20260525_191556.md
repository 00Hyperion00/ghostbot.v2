# HYP-005 Shadow Observation Quality / Slippage Risk Audit Deduplication + Recommendation Message Consistency Hotfix

- contract_version: `4B.4.3.6.6.25AB-H2`
- hotfix_version: `4B.4.3.6.6.25AB-H2`
- decision: `HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED`
- generated_at_utc: `2026-05-25T19:15:56Z`
- raw_observation_count: `1420`
- unique_observation_count: `20`
- duplicate_removed_count: `1400`
- shadow_observation_count: `20`
- shadow_sample_target: `30`
- progress_pct: `66.666667`
- matured_forward_return_count: `18`
- maturity_pending_count: `2`
- true_missing_required_fields_pct: `1.0`
- mean_forward_edge_bps: `15.509845`
- median_forward_edge_bps: `39.063688`
- profit_factor: `1.296959`
- win_rate_pct: `55.555556`
- max_slippage_proxy_bps: `15.634462`
- high_slippage_count: `2`

## Guardrail Decision

No training, reload, paper trading, live trading, POST requests, or order actions are approved by this audit.

## Reason Codes

- `MISSING_FINAL_RETURN_CLASSIFIED_AS_MATURITY_PENDING`
- `NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED`
- `OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED`
- `OBSERVATION_DUPLICATES_REMOVED`
- `RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED`
- `SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET`
- `SHADOW_SLIPPAGE_PROXY_HIGH`

## Warnings

- `MATURITY_PENDING_FORWARD_RETURNS_PRESENT`
- `OBSERVATION_DUPLICATES_REMOVED_FROM_QUALITY_METRICS`
- `SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET`
- `SHADOW_SLIPPAGE_PROXY_HIGH`

## Per-Symbol Quality

- ADAUSDT: count=1, matured=1, pending=0, mean_edge=59.031877, pf=999.0, max_slip=4.840614, flags=
- AVAXUSDT: count=3, matured=3, pending=0, mean_edge=-61.009818, pf=0.0, max_slip=12.717391, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- BNBUSDT: count=1, matured=1, pending=0, mean_edge=25.551141, pf=999.0, max_slip=3.290488, flags=
- BTCUSDT: count=1, matured=1, pending=0, mean_edge=158.648312, pf=999.0, max_slip=1.763543, flags=
- DOGEUSDT: count=4, matured=4, pending=0, mean_edge=-49.596507, pf=0.608081, max_slip=15.634462, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- ETHUSDT: count=2, matured=2, pending=0, mean_edge=109.121933, pf=13.67168, max_slip=7.236468, flags=
- LINKUSDT: count=2, matured=1, pending=1, mean_edge=52.576236, pf=999.0, max_slip=7.255521, flags=SYMBOL_MATURITY_PENDING_PRESENT
- LTCUSDT: count=1, matured=1, pending=0, mean_edge=76.165707, pf=999.0, max_slip=4.012632, flags=
- SOLUSDT: count=1, matured=0, pending=1, mean_edge=None, pf=None, max_slip=3.038488, flags=SYMBOL_MATURITY_PENDING_PRESENT
- XRPUSDT: count=4, matured=4, pending=0, mean_edge=17.593888, pf=1.301169, max_slip=11.729452, flags=

## Recommendation

HYP-005 shadow quality audit is deduped and review-required/collection-only with 20 unique shadow observations. Continue no-order shadow collection; do not train, reload, paper trade, live trade, or send orders. Review maturity-pending and slippage flags before any future transition gate.
