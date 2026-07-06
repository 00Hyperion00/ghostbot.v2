# 4B.4.3.6.6.52F — Paper Sandbox Paper Submit Adapter Arming Criteria

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436652F_paper_sandbox_paper_submit_adapter_arming_criteria.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436652F_paper_sandbox_paper_submit_adapter_arming_criteria.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436652F_paper_sandbox_paper_submit_adapter_arming_criteria.py --reports-dir .\reports\recovery --once-json
```
