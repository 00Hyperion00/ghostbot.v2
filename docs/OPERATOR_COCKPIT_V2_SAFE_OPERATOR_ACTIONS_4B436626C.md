# 4B.4.3.6.6.26C — Operator Cockpit V2 — Safe Operator Actions

## Scope

This overlay patch extends the local Operator Cockpit V2 with safe operator convenience actions while preserving the read-only security contract.

## Safe GET-only actions

- Refresh the dashboard snapshot.
- Re-run the local backend health probe.
- Open the safe action/source manifest.
- Download the current cockpit snapshot JSON.
- Open the latest HYP-005-R1 operator audit JSON.
- Download the latest isolated merged ledger JSONL.
- Download an in-memory evidence-pack ZIP containing only allowlisted isolated-R1 sources.

## Locked controls

The UI visibly lists, but does not activate:

- Emergency stop.
- Paper-mode enable.
- Live-mode enable.
- Model reload.
- Scheduler mutation.
- Symbol-set mutation.

These operations remain unavailable until a separate control-plane design and risk review are completed.

## Security constraints

- All enabled actions are HTTP GET endpoints.
- POST, PUT, PATCH and DELETE remain blocked with HTTP 405 and `READ_ONLY_DASHBOARD_MUTATION_BLOCKED`.
- Source exports use a fixed allowlist. Arbitrary paths are not accepted.
- Evidence packs are assembled in memory. The dashboard does not write export artifacts to the project directory.
- Individual source reads and total evidence-pack source bytes are bounded.
- Config, scheduler, model and trading state are not mutated.

## Runtime

Launch with:

```powershell
powershell -ExecutionPolicy Bypass -File tools\start_operator_cockpit_v2_4B436626C.ps1
```

The local address remains:

```text
http://127.0.0.1:8090/dashboard
```
