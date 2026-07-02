# 4B.4.3.6.6.33J-H1 — Operator Cockpit Recovery Plan Action Route Hotfix

This hotfix fixes a runtime-only 500 error in the 33J recovery-plan apply endpoints.

## Root cause

The recovery action routes called `require_operator_identity(context)` although the current security contract requires `require_operator_identity(context.get("operator_id"), action="...")`.

## Fixed endpoints

- `/api/cockpit/engine-position-recovery/create-plan`
- `/api/cockpit/engine-position-recovery/confirm-plan`
- `/api/cockpit/engine-position-recovery/verify-completion`
- `/api/cockpit/recovery-plan-apply/create-from-reviewed-candidate`
- `/api/cockpit/recovery-plan-apply/confirm-manual-external-recovery`
- `/api/cockpit/recovery-plan-apply/verify-no-mismatch`

## Safety contract

- No runtime position mutation.
- No automatic position mutation.
- No order-path change.
- No live-real enablement.
- No auth policy relaxation.
- Entry guard release still requires verified no-mismatch.
