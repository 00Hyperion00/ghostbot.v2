# 4B.4.3.6.6.26D-H2 — Operator Cockpit V2 — Native Desktop Export Bridge / Save-Dialog Download Hotfix

## Scope

This overlay hotfix repairs file-download actions inside the embedded pywebview desktop shell without changing the existing browser launcher, scheduler, model state, paper gate, live gate, or trading engine.

## Native desktop behavior

The desktop wrapper injects an embedded-window JavaScript interceptor after the pywebview page-loaded event. Only fixed cockpit action routes are intercepted.

Download actions:

- Snapshot JSON
- Evidence-pack ZIP
- Latest merged-ledger JSONL

Text-view actions:

- Latest audit JSON
- Safe-actions manifest JSON

Download actions open the operating system save dialog and write the selected destination atomically. Text-view actions open a modal inside the embedded desktop window.

## Security contract

- Only fixed action codes are accepted by the Python bridge.
- Only fixed `/api/operator-cockpit-v2/` loopback GET endpoints are fetched.
- External origins, redirects and arbitrary paths are blocked.
- Response buffering is bounded.
- A cancelled save dialog does not fetch or write a file.
- User-selected output writes are atomic.
- The browser-based 26C launcher remains unchanged.
- No config mutation.
- No scheduler mutation.
- No trading action.
- No paper or live enablement.

## Runtime

Restart the existing desktop shell after applying the overlay:

```powershell
powershell -ExecutionPolicy Bypass -File tools\start_operator_cockpit_v2_desktop_4B436626D.ps1
```
