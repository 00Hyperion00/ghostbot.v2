# 4B.4.3.6.6.51G — Paper Sandbox Duplicate Order Idempotency Lock Check

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436651G_paper_sandbox_duplicate_order_idempotency_lock_check.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436651G_paper_sandbox_duplicate_order_idempotency_lock_check.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436651G_paper_sandbox_duplicate_order_idempotency_lock_check.py --reports-dir .\reports\recovery --once-json
```
