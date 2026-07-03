# 4B.4.3.6.6.37H — Runtime Process Lock

## Scope

This patch closes `P0_RUNTIME_PROCESS_LOCK` as a static no-submit hardening baseline. It declares and probes:

1. single instance runtime lock requirement,
2. lock owner metadata requirement,
3. concurrent runtime start deny-by-default,
4. stale lock detection contract,
5. operator review requirement for stale lock recovery,
6. no automatic stale lock deletion,
7. no-submit runtime start denial,
8. no process kill / spawn / health probe side effects.

## Explicit non-actions

The patch does not create, delete, move, or mutate runtime lock files. It does not start or kill processes, activate runtime overlay, run a runtime health probe, open paper/live, or submit orders.

## Source gate

Requires latest `4B436637G_sqlite_audit_baseline_*_ready.json` under `reports/recovery` with decision:

`SQLITE_AUDIT_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_6_LOCKED`
