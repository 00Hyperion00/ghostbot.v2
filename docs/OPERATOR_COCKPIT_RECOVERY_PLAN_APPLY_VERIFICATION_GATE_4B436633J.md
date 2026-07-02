# 4B.4.3.6.6.33J — Operator Cockpit Recovery Plan Apply & Verification Gate

This patch builds on 33I-H1.

## Added

- Create Recovery Plan From Reviewed Candidate
- Confirm Manual External Recovery Plan
- Verify Engine Position After External Recovery
- Recovery Completion Ledger
- Entry Guard Release Only After Verified No-Mismatch
- Runtime helper `tools/check_cockpit_runtime_4B436633J.py`

## Safety Contract

- No automatic engine/runtime position mutation.
- No live-real enablement.
- No order path relaxation.
- No auth policy relaxation.
- Entry guard release is verified only after live read-only snapshot shows no active balance/position mismatch and no orphan recovery condition.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633J.py
pytest tests/test_operator_cockpit_4B436633J.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

## Runtime Check

```powershell
python tools/check_cockpit_runtime_4B436633J.py --token uzun-rastgele-token --operator operator-local
```
