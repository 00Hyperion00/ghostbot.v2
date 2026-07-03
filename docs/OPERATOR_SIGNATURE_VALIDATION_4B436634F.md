# 4B.4.3.6.6.34F — Operator Signature Validation

34F validates the 34E transition approval dry-run report and produces evidence for signature schema, digest matching, and no-submit approval.

## Scope

- Signature file schema ledger.
- Eligibility matrix digest match ledger.
- No-submit approval ledger.

## Safety behavior

A missing operator signature is accepted only as a no-unlock/no-submit state. A provided signature file is schema-checked and digest-checked, but 34F still does not unlock 34G and does not permit submit.

## Explicit non-goals

34F does not perform:

- exchange/network/order submit,
- paper/live/live-real transition,
- next phase unlock,
- runtime overlay,
- report deletion,
- file movement,
- archive execution,
- model training or reload.

## Expected decision

`OPERATOR_SIGNATURE_VALIDATION_READY_NO_SUBMIT_APPROVAL_LOCKED`
