4B.4.3.6.6.28D-H1 / 28E-H1
HYP-006-R1 Unicode-Safe + Absolute Python + Scheduler Wrapper + 28E Probe Hotfix

Purpose
- Fix 28D registration script Unicode path emission: Masa\u00fcst\u00fc must not appear in PS1.
- Use a Task Scheduler PowerShell wrapper instead of direct `python` action.
- Resolve absolute python.exe at registration-script execution time.
- Set PYTHONPATH=src inside scheduler runtime.
- Add missing --registration-json to canonical shadow cycle invocation.
- Write scheduler stdout/stderr logs.
- Fix 28E JSON loading for UTF-8 BOM files.
- Fix 28E Windows Task Scheduler probe for localized/non-UTF-8 PowerShell output.

Apply
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628D_H1_28E_H1_unicode_safe_absolute_python_scheduler_wrapper_probe_hotfix_patch.zip" `
  -DestinationPath . `
  -Force
python tools/apply_4B436628D_H1_28E_H1_scheduler_unicode_safe_hotfix.py

Check
$env:PYTHONPATH="src"
python tools/check_4B436628D_H1_28E_H1_scheduler_unicode_safe_hotfix.py --once-json

Test
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_scheduler_unicode_safe_hotfix_4B436628D_H1_28E_H1.py tests/test_hyp006_scheduler_execution_health_4B436628E.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Regenerate 28D-H1 registration script
$latest28C = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628C_hyp006_r1_no_order_shadow_runner_dry_run_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python tools/run_4B436628D_hyp006_shadow_registration_approval.py `
  --dry-run-report-json $latest28C.FullName `
  --out-dir .\reports\hyp006_r1_canonical `
  --symbols ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --operator-approval `
  --emit-registration-script `
  --review-ok

Review and register scheduler
$latestRegisterScript = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628D_register_hyp006_r1_canonical_no_order_shadow_scheduler_*.ps1 |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
notepad $latestRegisterScript.FullName

The Register-ScheduledTask line is intentionally commented. After operator review, uncomment that line in the script and run:
powershell -ExecutionPolicy Bypass -File $latestRegisterScript.FullName

Start and verify task
Start-ScheduledTask -TaskName TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection
Start-Sleep -Seconds 75
Get-ScheduledTaskInfo -TaskName TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection |
  Format-List LastRunTime,LastTaskResult,NextRunTime,NumberOfMissedRuns,TaskName

If LastTaskResult is not 0, read logs:
Get-Content .\reports\hyp006_r1_canonical\hyp006_scheduler_stdout.log -Tail 120
Get-Content .\reports\hyp006_r1_canonical\hyp006_scheduler_stderr.log -Tail 120

Run 28E health after LastTaskResult=0
$latest28DApproval = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_collection_registration_approval_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
$latest28DCycle = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_observation_logger_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
$latest28DLedger = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_ledger_*.jsonl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
python tools/run_4B436628E_hyp006_scheduler_execution_health.py `
  --registration-approval-json $latest28DApproval.FullName `
  --cycle-report-json $latest28DCycle.FullName `
  --ledger-jsonl $latest28DLedger.FullName `
  --out-dir .\reports\hyp006_r1_canonical `
  --operator-execution-review `
  --review-ok

Risk position
- No paper/live/order/training/reload enablement.
- Patch does not create/start/modify tasks by itself.
- Operator must explicitly review/uncomment registration script.
