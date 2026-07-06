# 4B.4.3.6.6.54C — Paper Sandbox Paper Order Rejection Budget Criteria

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436654C_paper_sandbox_paper_order_rejection_budget_criteria.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436654C_paper_sandbox_paper_order_rejection_budget_criteria.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436654C_paper_sandbox_paper_order_rejection_budget_criteria.py --reports-dir .\reports\recovery --once-json
```
