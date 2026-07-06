# 4B.4.3.6.6.58B — Max Live Notional Hard Cap Criteria

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436658B_paper_sandbox_max_live_notional_hard_cap_criteria.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436658B_paper_sandbox_max_live_notional_hard_cap_criteria.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436658B_paper_sandbox_max_live_notional_hard_cap_criteria.py --reports-dir .\reports\recovery --once-json
```
