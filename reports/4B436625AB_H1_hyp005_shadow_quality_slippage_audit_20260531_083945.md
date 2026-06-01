# HYP-005 Shadow Observation Quality / Slippage Risk Audit Deduplication + Recommendation Message Consistency Hotfix

- contract_version: `4B.4.3.6.6.25AB-H2`
- hotfix_version: `4B.4.3.6.6.25AB-H2`
- decision: `HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED`
- generated_at_utc: `2026-05-31T08:39:45Z`
- raw_observation_count: `2732`
- unique_observation_count: `27`
- duplicate_removed_count: `2705`
- shadow_observation_count: `27`
- shadow_sample_target: `30`
- progress_pct: `90.0`
- matured_forward_return_count: `25`
- maturity_pending_count: `2`
- true_missing_required_fields_pct: `0.740741`
- mean_forward_edge_bps: `-15.642778`
- median_forward_edge_bps: `16.225838`
- profit_factor: `0.783427`
- win_rate_pct: `56.0`
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
- AVAXUSDT: count=4, matured=4, pending=0, mean_edge=-44.076691, pf=0.03673, max_slip=12.717391, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- BNBUSDT: count=2, matured=2, pending=0, mean_edge=20.888489, pf=999.0, max_slip=3.988721, flags=
- BTCUSDT: count=1, matured=1, pending=0, mean_edge=158.648312, pf=999.0, max_slip=1.763543, flags=
- DOGEUSDT: count=4, matured=4, pending=0, mean_edge=-49.596507, pf=0.608081, max_slip=15.634462, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- ETHUSDT: count=3, matured=3, pending=0, mean_edge=2.516069, pf=1.033118, max_slip=7.236468, flags=
- LINKUSDT: count=4, matured=3, pending=1, mean_edge=-67.682101, pf=0.410343, max_slip=7.530573, flags=SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_MATURITY_PENDING_PRESENT
- LTCUSDT: count=1, matured=1, pending=0, mean_edge=76.165707, pf=999.0, max_slip=4.012632, flags=
- SOLUSDT: count=2, matured=1, pending=1, mean_edge=83.682008, pf=999.0, max_slip=4.799409, flags=SYMBOL_MATURITY_PENDING_PRESENT
- XRPUSDT: count=5, matured=5, pending=0, mean_edge=-48.036691, pf=0.558676, max_slip=11.729452, flags=SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW

## Recommendation

HYP-005 shadow quality audit is deduped and review-required/collection-only with 27 unique shadow observations. Continue no-order shadow collection; do not train, reload, paper trade, live trade, or send orders. Review maturity-pending and slippage flags before any future transition gate.
