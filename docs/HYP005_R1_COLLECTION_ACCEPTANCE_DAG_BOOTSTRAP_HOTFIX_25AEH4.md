# 4B.4.3.6.6.25AE-H4 — HYP-005-R1 Collection / Acceptance DAG Bootstrap and 25X Readiness Semantics Hotfix

## Scope

This hotfix removes the circular dependency between the 25X collection orchestrator and the downstream 25W paper-transition acceptance gate.

The runtime DAG is now explicit:

```text
25V logger -> 25X collection progress -> 25W paper-transition readiness -> 25Y operator audit
```

## 25X Semantics

25X collection readiness depends only on:

- the no-order candidate specification;
- the scoped 25V logger report;
- the scoped R1 ledger;
- safety flags remaining closed.

A previous 25W acceptance report is optional informational metadata. It is not a bootstrap prerequisite for 25X readiness. Unsafe approval or action flags in previous acceptance metadata still block collection.

25X now writes top-level operator summary fields:

```text
collection_status
shadow_observation_count
shadow_sample_target
progress_pct
acceptance_report_required_for_collection_ready
acceptance_report_seen
previous_acceptance_informational_only
```

Collection can be READY while status is `HYP005_SHADOW_COLLECTION_IN_PROGRESS`. Reaching the sample target changes the status to `HYP005_SHADOW_COLLECTION_TARGET_MET`; it does not grant paper or live permission.

## Safety

- Reports-dir isolation remains enforced.
- Strict explicit report chaining remains enforced.
- Baseline reports-root fallback remains forbidden in the R1 runtime chain.
- Paper/live/order/training/reload remain blocked.
- No scheduler registration or configuration mutation is performed by this hotfix.
