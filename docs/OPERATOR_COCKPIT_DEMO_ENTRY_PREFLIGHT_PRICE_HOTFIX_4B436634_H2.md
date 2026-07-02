# 4B.4.3.6.6.34-H2 Demo Entry Preflight Readiness & Mark Price Fallback Hotfix

Fixes two 34 runtime blockers after H1:

- Demo-entry gate did not recognize the 33M stabilized entry guard release when the legacy 33F guard payload omitted `entry_guard_release_verified`.
- Demo-entry dry-run could not compute quantity/notional when engine status did not expose `mark_price`.

34-H2 remains fail-closed for RED risk, unreconciled guards, missing filters, and missing price. It does not enable live-real trading and does not mutate engine position state. Operators may provide `mark_price` in the dry-run/filter body if the runtime status has no ticker price.
