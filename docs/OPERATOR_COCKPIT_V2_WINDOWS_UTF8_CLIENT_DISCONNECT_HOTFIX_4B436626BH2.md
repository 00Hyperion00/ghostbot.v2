# 4B.4.3.6.6.26B-H2 — Operator Cockpit V2 — Windows UTF-8 Empty-State Assertion / Client Disconnect Noise Suppression Hotfix

## Scope

This overlay hotfix keeps the dashboard read-only and changes only the Operator Cockpit V2 presentation/test layer.

## Repairs

- Forces UTF-8 decoding for the Node scatter-renderer regression harness on Windows.
- Preserves the Turkish MAE / MFE empty-state message across Windows locale settings.
- Suppresses expected client-side socket disconnect noise (`BrokenPipeError`, `ConnectionAbortedError`, `ConnectionResetError`) while preserving real server-side I/O exceptions.
- Keeps signed MAE / MFE scatter scaling from 26B-H1.
- Keeps POST, PUT, PATCH and DELETE blocked by the read-only cockpit contract.

## Safety

- No config mutation.
- No scheduler mutation.
- No trading action.
- No model reload.
- No Binance POST request.
