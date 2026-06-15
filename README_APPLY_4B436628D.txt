4B.4.3.6.6.28D HYP-006-R1 Canonical No-Order Shadow Collection / Scheduler Registration Operator Approval / Runtime Artifact Retention Policy

1) Apply
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628D_hyp006_r1_canonical_no_order_shadow_collection_scheduler_registration_operator_approval_runtime_artifact_retention_policy_patch.zip" -DestinationPath . -Force
python tools/apply_4B436628D_hyp006_shadow_registration_approval.py

2) Check
$env:PYTHONPATH="src"
python tools/check_4B436628D_hyp006_shadow_registration_approval.py --once-json

3) Tests
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_shadow_registration_approval_4B436628D.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

4) Generate operator approval pack
$latest28C = Get-ChildItem .\reports\hyp006_r1_canonical\4B436628C_hyp006_r1_no_order_shadow_runner_dry_run_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
New-Item -ItemType Directory -Force .\reports\hyp006_r1_canonical | Out-Null
python tools/run_4B436628D_hyp006_shadow_registration_approval.py `
  --dry-run-report-json $latest28C.FullName `
  --out-dir .\reports\hyp006_r1_canonical `
  --symbols ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --operator-approval `
  --emit-registration-script `
  --review-ok

5) Optional no-order cycle probe after approval pack
$latest28D = Get-ChildItem .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_collection_registration_approval_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latest28B = Get-ChildItem .\reports\hyp006_r1_candidate_spec\4B436628B_hyp006_r1_candidate_spec_registration_gate_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
python tools/run_4B436628D_hyp006_canonical_shadow_cycle.py `
  --registration-approval-json $latest28D.FullName `
  --registration-json $latest28B.FullName `
  --symbols ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --interval 4h `
  --days 30 `
  --out-dir .\reports\hyp006_r1_canonical `
  --review-ok

6) Commit if clean

git status --short
git add -A
git commit -m "4B.4.3.6.6.28D HYP-006-R1 canonical no-order shadow registration approval"
git tag -a 4B.4.3.6.6.28D -m "Accepted HYP-006-R1 canonical no-order shadow registration approval baseline"
git push
git push origin 4B.4.3.6.6.28D

Risk: This patch does not create or modify a scheduler task during apply/check. It emits a registration script for operator review. Paper/live/order/training/reload remain blocked.
