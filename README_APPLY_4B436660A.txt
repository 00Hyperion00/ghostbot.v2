# 4B.4.3.6.6.60A — Pre Live Governance Closure Review

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436660A_paper_sandbox_pre_live_governance_closure_review.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436660A_paper_sandbox_pre_live_governance_closure_review.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436660A_paper_sandbox_pre_live_governance_closure_review.py --reports-dir .\reports\recovery --once-json
```
