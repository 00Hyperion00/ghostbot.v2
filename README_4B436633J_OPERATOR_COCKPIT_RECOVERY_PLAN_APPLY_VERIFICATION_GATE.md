# 4B.4.3.6.6.33J — Operator Cockpit Recovery Plan Apply & Verification Gate

## Scope

- Create Recovery Plan From Reviewed Candidate
- Confirm Manual External Recovery Plan
- Verify Engine Position After External Recovery
- Recovery Completion Ledger
- Entry Guard Release Only After Verified No-Mismatch

## Safety Contract

- No live-real enablement.
- No order path relaxation.
- No auth policy relaxation.
- No automatic engine/runtime position mutation.
- Entry guard release requires verified no-mismatch from a fresh read-only runtime snapshot.

## Install

```powershell
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633J_operator_cockpit_recovery_plan_apply_verification_gate_patch.zip" `
  -DestinationPath . `
  -Force

python apply_4B436633J_operator_cockpit_recovery_plan_apply_verification_gate.py
```

## Test

```powershell
python tools/compile_operator_cockpit_4B436633J.py
pytest tests/test_operator_cockpit_4B436633J.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```
