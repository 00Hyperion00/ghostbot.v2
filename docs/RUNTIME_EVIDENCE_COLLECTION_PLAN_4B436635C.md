# 4B.4.3.6.6.35C — Runtime Evidence Collection Plan

35C is a planning-only governance phase.

## Acceptance

- Source 35B READY report exists.
- 35B safety fields remain false.
- Evidence Source Registry is complete.
- Collection Runbook Matrix is complete.
- No-Submit Collection Boundary is locked.

## Boundary

The patch must not collect evidence, call exchange/private APIs, submit orders, enable paper/live mode, enable runtime overlay, train, reload, move/delete files, or perform archive/deduplication actions.

Expected decision:

```text
RUNTIME_EVIDENCE_COLLECTION_PLAN_READY_NO_SUBMIT_COLLECTION_BOUNDARY_LOCKED
```
