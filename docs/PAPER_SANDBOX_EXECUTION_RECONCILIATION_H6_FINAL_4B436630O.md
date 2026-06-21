# 4B.4.3.6.6.30O-H6 Reconciliation Module / Checker Final

Finalizes 30O by replacing the reconciliation module and checker stack with deterministic file-ledger and direct-ledger-event probes.

Fixes:
- `ledger_event` and file-ledger signatures.
- deterministic SQLite mirror in a temp DB during checker probe.
- H1-H5 wrappers now delegate to the repaired target 30O checker.
- run tool uses a fresh SQLite path per evidence run to avoid stale mirror collisions.

Risk posture remains unchanged: no exchange submit, no live-real.
