# 4B.4.3.6.6.33I-H1 Operator Cockpit Engine Position Recovery Key Hotfix

Purpose: fix the 33I runtime snapshot/WebSocket failure caused by missing `_engine_position_recovery_key`.

## Scope

- Adds the missing symbol-scoped recovery persistence key helper.
- Keeps the 33I no-auto-position-mutation contract.
- Does not change live-real, order path, auth policy, strategy thresholds, or runtime position state.

## Expected Runtime Result

`/api/cockpit/snapshot` and `/ws/cockpit` no longer fail with:

```text
NameError: name '_engine_position_recovery_key' is not defined
```

Entry guard remains blocked until engine position recovery is actually verified.
