# 4B.4.3.6.6.34-H3 — Demo Entry Execution Fill Awareness

This hotfix hardens 34 demo-only entry execution after successful dry-run/filter/intent/authorization.

## Scope

- Binds `force-buy` to a concrete engine/exchange order result when available.
- Detects order id, client order id, status, executed quantity, pending order, position and protective exit.
- Consumes demo authorization only if an accepted order or position/pending order is detected.
- Records `latest_force_buy_execution` and execution ledger.
- Records post-entry protective-exit verification immediately after force-buy and on explicit verification.
- Keeps no-fill/no-protection states fail-closed.

## Non-goals

- No live-real enablement.
- No auth policy relaxation.
- No engine position mutation.
- No automatic retry.
- No bypass when the engine returns no order/fill/position evidence.
