# 4B.4.3.6.6.26B-H3 — Operator Cockpit V2 — Windows Mutation Request Body Drain / HTTP 405 Contract Preservation Hotfix

## Scope

This overlay hotfix preserves the read-only Operator Cockpit contract on Windows when mutation requests contain a request body.

## Repairs

- Drains small blocked POST, PUT, PATCH and DELETE request bodies before sending the HTTP 405 response.
- Caps request-body draining at 64 KiB and closes the connection for oversized, malformed or unsupported chunked mutation payloads.
- Preserves the stable JSON error code: `READ_ONLY_DASHBOARD_MUTATION_BLOCKED`.
- Adds an explicit `Connection: close` header when a safe connection close is required.
- Flushes response output when the writer supports flushing.
- Keeps Windows UTF-8 handling, client-disconnect noise suppression and signed MAE / MFE scatter rendering.

## Safety

- Mutation payloads are consumed only as bytes and never parsed or executed.
- No config mutation.
- No scheduler mutation.
- No trading action.
- No model reload.
- No Binance POST request.
