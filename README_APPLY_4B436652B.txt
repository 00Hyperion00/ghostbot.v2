# 4B.4.3.6.6.52B — Paper Sandbox External Runtime Start Handoff For Paper Soak

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436652B_paper_sandbox_external_runtime_start_handoff_for_paper_soak.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436652B_paper_sandbox_external_runtime_start_handoff_for_paper_soak.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436652B_paper_sandbox_external_runtime_start_handoff_for_paper_soak.py --reports-dir .\reports\recovery --once-json
```
