# 4B.4.3.6.6.52A — Paper Sandbox Controlled Paper Runtime Enablement Review

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436652A_paper_sandbox_controlled_paper_runtime_enablement_review.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436652A_paper_sandbox_controlled_paper_runtime_enablement_review.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436652A_paper_sandbox_controlled_paper_runtime_enablement_review.py --reports-dir .\reports\recovery --once-json
```
