4B.4.3.6.6.28G HYP-006-R1 Shadow Sample Expansion / Acceptance Tracking / Operator Cockpit Continuity Delta Evidence

1) Patch uygula

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_operator_cockpit_continuity_delta_evidence_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436628G_hyp006_shadow_sample_expansion_tracking.py

2) Checker

$env:PYTHONPATH="src"
python tools/check_4B436628G_hyp006_shadow_sample_expansion_tracking.py --once-json

3) Test

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_shadow_sample_expansion_tracking_4B436628G.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

4) 28G acceptance tracking üret

$latest28F = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628F_hyp006_r1_operator_cockpit_baseline_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$latestLedger = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_ledger_*.jsonl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python tools/run_4B436628G_hyp006_shadow_sample_expansion_tracking.py `
  --operator-cockpit-baseline-json $latest28F.FullName `
  --ledger-jsonl $latestLedger.FullName `
  --out-dir .\reports\hyp006_r1_canonical `
  --operator-continuity-review `
  --review-ok

5) Raporu oku

$latest28G = Get-ChildItem `
  .\reports\hyp006_r1_canonical\4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Get-Content $latest28G.FullName -Raw -Encoding UTF8

6) Commit / tag

git status --short
git add -A
git commit -m "4B.4.3.6.6.28G HYP-006-R1 shadow sample expansion tracking"
git tag -a 4B.4.3.6.6.28G -m "Accepted HYP-006-R1 shadow sample expansion acceptance tracking"
git push
git push origin 4B.4.3.6.6.28G

Risk: Paper/live/order/training/reload kapalı kalır. 28G sadece no-order acceptance tracking üretir.
