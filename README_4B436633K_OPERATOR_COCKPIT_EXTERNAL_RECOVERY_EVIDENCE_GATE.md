# 4B.4.3.6.6.33K — Operator Cockpit External Recovery Evidence Gate

This patch builds on 33J-H1 and adds the external/manual recovery evidence gate.

## Added

- Manual Recovery Evidence Capture
- Read-Only Post-Recovery Balance Snapshot
- No-Mismatch Preflight
- Verify-No-Mismatch Safe Apply
- Entry Guard Release Only With Evidence + Fresh Snapshot
- Runtime helper `tools/check_cockpit_runtime_4B436633K.py`

## Safety Contract

- No automatic engine/runtime position mutation.
- No order path relaxation.
- No live-real enablement.
- No auth policy relaxation.
- Verify-no-mismatch safe apply is fail-closed unless evidence exists, post-recovery snapshot is fresh, and mismatch/orphan state is clear.

## Runtime Flow

1. Confirmed 33J recovery plan must exist.
2. Capture external recovery evidence.
3. Capture a fresh read-only post-recovery balance snapshot.
4. Run no-mismatch preflight.
5. Run verify-no-mismatch safe apply only if the preflight passes.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633K.py
pytest tests/test_operator_cockpit_4B436633K.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```
