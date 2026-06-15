4B.4.3.6.6.27G-H5
HYP-005-R1 Branch Review / Negative Expectancy Closure Evidence / No-Promotion Decision Pack

1) Proje klasörüne geçin:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) ZIP dosyasını açın:

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627G_H5_hyp005_r1_branch_review_negative_expectancy_closure_evidence_no_promotion_decision_pack_patch.zip" `
  -DestinationPath . `
  -Force

3) Patch'i uygulayın:

python tools/apply_4B436627GH5_hyp005_branch_review_closure.py

4) Read-only checker:

$env:PYTHONPATH="src"
python tools/check_4B436627GH5_hyp005_branch_review_closure.py --once-json

5) Hedefli test:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp005_branch_review_closure_4B436627GH5.py

6) Derleme kontrolü:

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

7) Closure evidence pack çalıştırma:

$latestLedger = Get-ChildItem .\reports\hyp005_r1_canonical\4B436625X_hyp005_shadow_merged_ledger_*.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestH3 = Get-ChildItem .\reports\hyp005_r1_canonical\4B436627GH3_hyp005_shadow_stagnation_diagnostics_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestH4 = Get-ChildItem .\reports\hyp005_r1_canonical\4B436627GH4_hyp005_shadow_parameter_sensitivity_matrix_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1

python tools/run_4B436627GH5_hyp005_branch_review_closure.py `
  --ledger-jsonl $latestLedger.FullName `
  --h3-diagnostics-json $latestH3.FullName `
  --h4-sensitivity-json $latestH4.FullName `
  --out-dir .\reports\hyp005_r1_canonical `
  --review-ok

Geri alma:

python tools/rollback_4B436627GH5_hyp005_branch_review_closure.py
