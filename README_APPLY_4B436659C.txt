# 4B.4.3.6.6.59C — Operator Typed Live Approval Contract

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436659C_paper_sandbox_operator_typed_live_approval_contract.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436659C_paper_sandbox_operator_typed_live_approval_contract.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436659C_paper_sandbox_operator_typed_live_approval_contract.py --reports-dir .\reports\recovery --once-json
```
