# 4B.4.3.6.6.26D-H2-H1 — Operator Cockpit V2 — Native Export Integration Test Fixture Ledger Seed / Deterministic 404 Contract Hotfix

## Scope

This overlay corrects the native desktop export bridge integration-test fixture. It does not change desktop-wrapper production code.

## Root cause

The H2 integration test called:

```text
/api/operator-cockpit-v2/export/latest-ledger
```

against a temporary project directory without an isolated R1 merged-ledger source. The read-only cockpit correctly returned HTTP `404`, while the test incorrectly expected a `200` payload containing `BTCUSDT`.

## Repair

- Seeds one deterministic isolated-R1 merged-ledger JSONL row before the HTTP `200` native-export integration scenario.
- Verifies that the seeded ledger contains `BTCUSDT`.
- Adds a separate missing-ledger contract test that explicitly expects `NATIVE_DESKTOP_EXPORT_HTTP_ERROR: 404`.
- Preserves the evidence-pack size-limit test with a seeded ledger.
- Preserves external endpoint fail-closed behavior.

## Security

- Production source code is not modified.
- Config is not mutated.
- Scheduler is not mutated.
- Trading state is not mutated.
- Paper and live gates are not changed.
- The native desktop export allowlist remains unchanged.
