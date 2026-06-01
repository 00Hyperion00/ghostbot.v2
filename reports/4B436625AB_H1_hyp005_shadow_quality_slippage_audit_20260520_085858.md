# HYP-005 Shadow Observation Quality / Slippage Risk Audit Deduplication + Recommendation Message Consistency Hotfix

- contract_version: `4B.4.3.6.6.25AB-H2`
- hotfix_version: `4B.4.3.6.6.25AB-H2`
- decision: `HYP005_SHADOW_QUALITY_AUDIT_BLOCK`
- generated_at_utc: `2026-05-20T08:58:58Z`
- raw_observation_count: `402`
- unique_observation_count: `16`
- duplicate_removed_count: `386`
- shadow_observation_count: `16`
- shadow_sample_target: `30`
- progress_pct: `53.333333`
- matured_forward_return_count: `12`
- maturity_pending_count: `4`
- true_missing_required_fields_pct: `1.25`
- mean_forward_edge_bps: `-60.566197`
- median_forward_edge_bps: `-19.481046`
- profit_factor: `0.226913`
- win_rate_pct: `33.333333`
- max_slippage_proxy_bps: `15.634462`
- high_slippage_count: `2`

## Guardrail Decision

No training, reload, paper trading, live trading, POST requests, or order actions are approved by this audit.

## Reason Codes

- `BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION`
- `MATURED_MEAN_FORWARD_EDGE_NEGATIVE`
- `MATURED_PROFIT_FACTOR_LOW`
- `NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED`
- `OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED`
- `OBSERVATION_DUPLICATES_REMOVED`
- `RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED`
- `SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET`
- `SHADOW_SLIPPAGE_PROXY_HIGH`
- `TRUE_REQUIRED_FIELDS_MISSING_HIGH`

## Warnings

- `MATURED_MEAN_FORWARD_EDGE_NEGATIVE`
- `MATURED_PROFIT_FACTOR_LOW`
- `OBSERVATION_DUPLICATES_REMOVED_FROM_QUALITY_METRICS`
- `SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET`
- `SHADOW_SLIPPAGE_PROXY_HIGH`

## Per-Symbol Quality

- ADAUSDT: count=1, matured=1, pending=0, mean_edge=59.031877, pf=999.0, max_slip=4.840614, flags=
- AVAXUSDT: count=3, matured=3, pending=0, mean_edge=-61.009818, pf=0.0, max_slip=12.717391, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- BNBUSDT: count=1, matured=1, pending=0, mean_edge=25.551141, pf=999.0, max_slip=3.290488, flags=
- DOGEUSDT: count=3, matured=2, pending=1, mean_edge=-253.096006, pf=0.0, max_slip=15.634462, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_MATURITY_PENDING_PRESENT
- ETHUSDT: count=1, matured=1, pending=0, mean_edge=-17.222962, pf=0.0, max_slip=7.236468, flags=SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- LINKUSDT: count=2, matured=1, pending=1, mean_edge=52.576236, pf=999.0, max_slip=7.255521, flags=SYMBOL_MATURITY_PENDING_PRESENT
- LTCUSDT: count=1, matured=1, pending=0, mean_edge=76.165707, pf=999.0, max_slip=4.012632, flags=
- SOLUSDT: count=1, matured=0, pending=1, mean_edge=None, pf=None, max_slip=3.038488, flags=SYMBOL_MATURITY_PENDING_PRESENT
- XRPUSDT: count=3, matured=2, pending=1, mean_edge=-116.837447, pf=0.0, max_slip=11.729452, flags=SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_MATURITY_PENDING_PRESENT

## Recommendation

HYP-005 shadow quality audit is blocked with 16 unique shadow observations after canonical deduplication. Keep paper/live/order disabled. Resolve blockers before any transition gate: TRUE_REQUIRED_FIELDS_MISSING_HIGH. Review warnings: MATURED_MEAN_FORWARD_EDGE_NEGATIVE, MATURED_PROFIT_FACTOR_LOW, OBSERVATION_DUPLICATES_REMOVED_FROM_QUALITY_METRICS, SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET, SHADOW_SLIPPAGE_PROXY_HIGH.
