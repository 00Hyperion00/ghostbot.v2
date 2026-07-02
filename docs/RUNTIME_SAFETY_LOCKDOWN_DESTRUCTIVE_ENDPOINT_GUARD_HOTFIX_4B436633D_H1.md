# 4B.4.3.6.6.33D-H1 — Destructive Endpoint Guard Coverage Hotfix

Bu hotfix, 33D `Runtime Safety Lockdown` çıktısında unguarded görünen üç legacy FastAPI endpointini fail-closed guard ile kapatır:

- `POST /balance-sync`
- `POST /risk-reset`
- `POST /safe-mode/toggle`

Bu endpointler `src/tradebot/api.py` içinde legacy yüzeydir. Cockpit tarafındaki `/api/...` endpointler zaten operator / confirmation / runtime-lock guard evidence ile korunmaktadır. Bu patch legacy destructive endpointleri doğrudan bloke eder.

## Safety contract

- Exchange submit yapmaz.
- Trading action yapmaz.
- Runtime overlay açmaz.
- Training yapmaz.
- Reload yapmaz.
- Paper/live/live-real onayı vermez.
- Destructive cleanup yapmaz.

Beklenen 33D-H1 kararı:

```text
DESTRUCTIVE_ENDPOINT_GUARD_COVERAGE_HOTFIX_READY
```

Beklenen 33D rerun kararı:

```text
RUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED
```
