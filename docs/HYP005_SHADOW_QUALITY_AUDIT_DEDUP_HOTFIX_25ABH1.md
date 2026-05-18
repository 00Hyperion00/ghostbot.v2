# 4B.4.3.6.6.25AB-H1 — HYP-005 Shadow Quality Audit Deduplication Hotfix

This hotfix updates the HYP-005 shadow observation quality / slippage risk audit to use a canonical observation key instead of trusting the raw `observation_id` alone.

## Why

The 25V `observation_id` may include a rolling row index. The same symbol/timeframe/candle can therefore be counted multiple times when `--include-all` reads historical 25V ledgers across scheduler cycles.

25AB-H1 dedupes with this canonical observation key:

```text
hypothesis_id | strategy_family | symbol | timeframe | timestamp_utc
```

When duplicates are found, the audit keeps the best row using this priority:

```text
prefer matured final forward return → data_quality_ok → fewer missing required fields → richer numeric fields
```

## Safety

Paper/live remain blocked. This hotfix does not train, reload, paper trade, live trade, mutate config, send POST requests, or send orders.

## Expected Output

The report now includes:

```text
deduplication.raw_observation_count
deduplication.unique_observation_count
deduplication.duplicate_removed_count
quality_summary.shadow_observation_count
```

The quality metrics are calculated only on unique observations.
