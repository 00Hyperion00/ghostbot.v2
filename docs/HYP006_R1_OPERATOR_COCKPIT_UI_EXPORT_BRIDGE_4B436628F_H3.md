# 4B.4.3.6.6.28F-H3 Operator Cockpit UI Label / Native Export Bridge Hotfix

Read-only hotfix for HYP-006-R1 cockpit parity.

## Scope

- Replace legacy `HYP-005-R1 Shadow Validation` section label with `HYP-006-R1 Shadow Sample Expansion`.
- Update read-only dashboard badges to `28F-H3`.
- Normalize native desktop export HTTP 412 failures to an operator-safe fail-closed message.
- Preserve all paper/live/training/reload/order gates as false.

## Non-goals

- No config mutation.
- No scheduler mutation.
- No training or reload.
- No paper/live/order enablement.
