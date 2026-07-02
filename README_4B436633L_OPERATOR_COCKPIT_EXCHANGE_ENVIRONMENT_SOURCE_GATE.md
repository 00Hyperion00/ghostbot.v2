# 4B.4.3.6.6.33L — Operator Cockpit Exchange Environment Consistency & Fresh Balance Source Gate

This patch builds on 33K and adds a fresh-source integrity gate for no-mismatch verification.

## Added

- Config Environment Audit
- Demo Spot vs Engine Balance Source Verification
- Fresh Exchange Balance Read Requirement
- Stale Engine Balance Snapshot Rejection
- No-Mismatch Verification Only From Verified Fresh Source
- Runtime helper `tools/check_cockpit_runtime_4B436633L.py`

## Safety Contract

- `engine_status_balances` is not sufficient for no-mismatch verification.
- No entry guard release unless a fresh exchange balance source is verified.
- No automatic engine/runtime position mutation.
- No order path relaxation.
- No live-real enablement.
- No auth policy relaxation.

## Runtime Flow

1. Verify config environment consistency.
2. Capture a fresh exchange balance source from the engine/client layer.
3. Capture the 33K post-recovery snapshot.
4. Run the 33K no-mismatch preflight; it now requires 33L fresh source verification.
5. Run 33K safe apply only after preflight passes.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633L.py
pytest tests/test_operator_cockpit_4B436633L.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```
