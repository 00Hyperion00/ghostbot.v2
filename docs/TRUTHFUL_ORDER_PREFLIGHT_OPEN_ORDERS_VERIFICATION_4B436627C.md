# 4B.4.3.6.6.27C — Truthful Order Preflight / Open-Orders Verification

## Scope

This overlay replaces fabricated preflight-success fields with truthful execution evidence.

For `ENTRY_NEW_RISK`, the exchange adapter now performs:

1. Exchange-level execution-policy evaluation before any network request.
2. Signed `GET /api/v3/openOrders` query.
3. Fail-closed block when existing open orders are detected.
4. Signed `POST /api/v3/order/test` validation.
5. Real order submission only after both checks pass.

For `EXIT_RISK_REDUCING`, entry-only checks are deliberately not performed. Logs report `false` / `null` instead of fabricated values.

## Safety

- No scheduler mutation.
- No runtime configuration mutation.
- No paper/live enablement.
- No real order is submitted by the checker tool.
- Open-orders or order-test uncertainty denies new-risk entry.
