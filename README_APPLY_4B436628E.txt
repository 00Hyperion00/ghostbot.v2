4B.4.3.6.6.28E — HYP-006-R1 Canonical Shadow Scheduler Execution / Windows Task Registration Health Verify / No-Order Ledger Continuity Evidence Pack

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628E_hyp006_r1_canonical_shadow_scheduler_execution_windows_task_registration_health_verify_no_order_ledger_continuity_evidence_pack_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436628E_hyp006_scheduler_execution_health.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436628E_hyp006_scheduler_execution_health.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_hyp006_scheduler_execution_health_4B436628E.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Before health verification, operator must register the no-order scheduler task from the reviewed 28D registration script. The 28E patch does not create the task.

Run health verification:
  $latest28DApproval = Get-ChildItem .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_collection_registration_approval_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $latest28DCycle = Get-ChildItem .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_observation_logger_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $latest28DLedger = Get-ChildItem .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_ledger_*.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  python tools/run_4B436628E_hyp006_scheduler_execution_health.py --registration-approval-json $latest28DApproval.FullName --cycle-report-json $latest28DCycle.FullName --ledger-jsonl $latest28DLedger.FullName --out-dir .\reports\hyp006_r1_canonical --operator-execution-review --review-ok

Commit after PASS:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.28E HYP-006-R1 scheduler execution health evidence pack"
  git tag -a 4B.4.3.6.6.28E -m "Accepted HYP-006-R1 scheduler execution health baseline"
  git push
  git push origin 4B.4.3.6.6.28E

Rollback:
  python tools/rollback_4B436628E_hyp006_scheduler_execution_health.py

Safety contract:
  - no scheduler mutation by patch
  - no order action
  - no paper/live enablement
  - no training/reload
