# 4B.4.3.6.6.51B — Paper Sandbox Paper Submit Typed Operator Approval Contract

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436651B_paper_sandbox_paper_submit_typed_operator_approval_contract.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436651B_paper_sandbox_paper_submit_typed_operator_approval_contract.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436651B_paper_sandbox_paper_submit_typed_operator_approval_contract.py --reports-dir .\reports\recovery --once-json
```
