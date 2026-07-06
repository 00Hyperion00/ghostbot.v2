# 4B.4.3.6.6.57C — Withdrawal Permission Denial Criteria

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436657C_paper_sandbox_withdrawal_permission_denial_criteria.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436657C_paper_sandbox_withdrawal_permission_denial_criteria.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436657C_paper_sandbox_withdrawal_permission_denial_criteria.py --reports-dir .\reports\recovery --once-json
```
