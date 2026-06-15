4B.4.3.6.6.28C HYP-006-R1 No-Order Shadow Runner Dry-Run / Operator Registration Approval Gate / Canonical Scheduler Registration Preflight

Apply:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628C_hyp006_r1_no_order_shadow_runner_dry_run_operator_registration_approval_gate_canonical_scheduler_registration_preflight_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436628C_hyp006_shadow_runner_dry_run.py

Check:

$env:PYTHONPATH="src"
python tools/check_4B436628C_hyp006_shadow_runner_dry_run.py --once-json

Test:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_shadow_runner_dry_run_4B436628C.py

Compile:

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run dry-run with public market data:

$latest28B = Get-ChildItem `
  .\reports\hyp006_r1_candidate_spec\4B436628B_hyp006_r1_candidate_spec_registration_gate_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

New-Item -ItemType Directory -Force .\reports\hyp006_r1_canonical | Out-Null

python tools/run_4B436628C_hyp006_shadow_runner_dry_run.py `
  --registration-json $latest28B.FullName `
  --symbols ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --interval 4h `
  --days 30 `
  --out-dir .\reports\hyp006_r1_canonical `
  --review-ok

Read report:

$latest28C = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628C_hyp006_r1_no_order_shadow_runner_dry_run_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Get-Content $latest28C.FullName -Raw -Encoding UTF8

Commit:

git status --short
git add -A
git commit -m "4B.4.3.6.6.28C HYP-006-R1 no-order shadow runner dry-run gate"
git tag -a 4B.4.3.6.6.28C -m "Accepted HYP-006-R1 no-order shadow runner dry-run gate baseline"
git push
git push origin 4B.4.3.6.6.28C

Rollback:

python tools/rollback_4B436628C_hyp006_shadow_runner_dry_run.py

Safety:

28C does not create or modify scheduler tasks. It does not start shadow collection. It does not train, reload, paper trade, live trade, or send orders.
