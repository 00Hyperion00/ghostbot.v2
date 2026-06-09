# 4B.4.3.6.6.25V-H1 — HYP-005 Shadow Observation Stable Identity / Rolling-Ordinal Drift Hotfix

## Scope

This overlay stabilizes future HYP-005 25V logger ledger identities without mutating scheduler configuration, existing historical report files, trading state, paper mode or live mode.

## Problem

Legacy observation IDs include a rolling-window ordinal. When the 30-day candle window advances, the same candle receives a different ordinal and therefore a misleadingly different raw ID.

## Stable identity

Future 25V ledger rows use:

```text
hypothesis_id + symbol + timeframe + timestamp_utc
```

Example:

```text
HYP-005-BNBUSDT-4h-2026-06-05T040000Z
```

The former ordinal-bearing ID is retained as `legacy_observation_id` for audit traceability.

## Runtime integration

The patch preserves the original 25V runner as:

```text
tools/run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py
```

The original scheduler path becomes a wrapper. It executes the original no-order logger and atomically normalizes only newly emitted 25V ledger files.

## Safety

- Existing historical ledgers are not rewritten.
- Existing canonical samples are not deleted.
- Scheduler configuration is not changed.
- No model reload occurs.
- No paper or live mode is enabled.
- No order action is performed.

## Rollback

The original logger runner can be restored without changing scheduler configuration:

```powershell
python tools/rollback_4B436625V_H1_hyp005_shadow_observation_stable_identity_hotfix.py
```
