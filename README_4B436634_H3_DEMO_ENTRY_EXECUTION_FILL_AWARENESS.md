# 4B.4.3.6.6.34-H3 — Demo Entry Execution Fill Awareness Hotfix

## Purpose

34-H2 proved demo entry preflight, but `force-buy` could return success while no position/fill/protective-exit was verified. H3 makes force-buy execution fill-aware and fail-closed.

## Adds

- Force Buy Result Binding
- Authorization Consumption Safety
- Post-Entry Position Detection
- Protective Exit Mandatory Verification
- No-Fill No-Protection Fail-Closed

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436634_H3_demo_entry_execution_fill_awareness_patch.zip" `
  -DestinationPath . `
  -Force
python apply_4B436634_H3_demo_entry_execution_fill_awareness.py
```

## Test

```powershell
python tools/compile_operator_cockpit_4B436634_H3.py
pytest tests/test_operator_cockpit_4B436634_H3.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

## Safety

- Does not enable live-real.
- Does not relax auth policy.
- Does not mutate engine position state.
- Does not consume demo authorization unless an order/pending/position signal is detected.
- Keeps unprotected/no-fill execution fail-closed.
