# 4B.4.3.6.6.50B — Paper Sandbox Typed Controlled Paper Trading Soak Approval Ledger

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436650B_paper_sandbox_typed_controlled_paper_trading_soak_approval_ledger.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436650B_paper_sandbox_typed_controlled_paper_trading_soak_approval_ledger.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436650B_paper_sandbox_typed_controlled_paper_trading_soak_approval_ledger.py --reports-dir .\reports\recovery --once-json
```
