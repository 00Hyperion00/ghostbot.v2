# 4B.4.3.6.6.33M — Operator Cockpit Engine Status Balance Cache Reconciliation

This patch builds on 33L and fixes the final cockpit state inconsistency where `engine_status_balances` can continue to drive RED risk state after 33K/33L safe apply has verified no active mismatch from a fresh exchange balance source.

## Added

- Verified Fresh Source To Runtime Snapshot Override
- Stale Engine Balance Invalidated
- Risk Badge Recompute From Verified Fresh Source
- Entry Guard Final Release Consistency
- Stable entry release after `verify-no-mismatch-safe-apply` when the safe apply was verified from fresh exchange source
- Runtime helper `tools/check_cockpit_runtime_4B436633M.py`

## Safety Contract

- No automatic engine/runtime position mutation.
- No order path relaxation.
- No live-real enablement.
- No auth policy relaxation.
- No trading action is executed by this patch.
- The override is cockpit-state-only and activates only after 33K safe apply and 33L fresh-source no-mismatch verification.
- If an unrelated active anomaly is present, stale cache override remains disabled.

## Runtime Flow

1. Capture fresh exchange balance with 33L.
2. Capture post-recovery snapshot with 33K.
3. Run no-mismatch preflight.
4. Run safe apply.
5. 33M invalidates stale `engine_status_balances` for cockpit risk/entry decisions when safe apply was verified from fresh exchange source.
6. Risk badge and entry guard are recomputed from the verified fresh source view.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633M.py
pytest tests/test_operator_cockpit_4B436633M.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```
