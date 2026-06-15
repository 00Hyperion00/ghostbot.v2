4B.4.3.6.6.28F HYP-006-R1 Shadow Operator Cockpit Dashboard Seed / Acceptance Baseline Metrics / No-Order Continuity Monitor

Apply:
  python tools/apply_4B436628F_hyp006_operator_cockpit_baseline.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436628F_hyp006_operator_cockpit_baseline.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_hyp006_operator_cockpit_baseline_4B436628F.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $latest28E = Get-ChildItem .\reports\hyp006_r1_canonical\4B436628E_hyp006_r1_scheduler_execution_health_verify_*.json |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  $latestLedger = Get-ChildItem .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_ledger_*.jsonl |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  python tools/run_4B436628F_hyp006_operator_cockpit_baseline.py `
    --scheduler-health-json $latest28E.FullName `
    --ledger-jsonl $latestLedger.FullName `
    --out-dir .\reports\hyp006_r1_canonical `
    --operator-dashboard-review `
    --review-ok

Safety:
  - read-only
  - no scheduler mutation
  - no config mutation
  - no training/reload
  - no paper/live
  - no orders
