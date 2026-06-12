# 4B.4.3.6.6.25AE-H5 — HYP-005-R1 Canonical Epoch Hardening

## Scope

This patch aligns the HYP-005-R1 canonical no-order shadow runtime:

- Creates a manual-registration Windows Task Scheduler helper for a new canonical task.
- Preserves the legacy R1 task in Disabled state.
- Runs an explicit fail-closed `25V → 25X → 25W → 25Y → chain checks` DAG.
- Uses `reports\hyp005_r1_canonical` as the canonical epoch directory.
- Emits UTC artifact stamps with an explicit `Z` suffix.
- Prevents 25W collection-report metadata from being counted as a ledger source.
- Makes Operator Cockpit prefer canonical epoch sources while retaining legacy fallback for pre-H5 fixtures.

## Safety

Patch application does **not** register, enable, disable or delete a Windows task. Registration remains a separate manual operator action.

The cycle contains no training, reload, paper, live or order action.

## Manual registration after smoke tests

```powershell
powershell -ExecutionPolicy Bypass -File `
  tools\register_hyp005_r1_canonical_epoch_task_4B436625AEH5.ps1
```

## Disable the canonical task without deleting it

```powershell
powershell -ExecutionPolicy Bypass -File `
  tools\disable_hyp005_r1_canonical_epoch_task_4B436625AEH5.ps1
```
