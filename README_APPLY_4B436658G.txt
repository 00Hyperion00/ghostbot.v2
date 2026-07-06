# 4B.4.3.6.6.58G — Emergency Kill-Switch Drill Criteria

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436658G_paper_sandbox_emergency_kill_switch_drill_criteria.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436658G_paper_sandbox_emergency_kill_switch_drill_criteria.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436658G_paper_sandbox_emergency_kill_switch_drill_criteria.py --reports-dir .\reports\recovery --once-json
```
