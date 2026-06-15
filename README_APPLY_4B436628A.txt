4B.4.3.6.6.28A
New Hypothesis Candidate Discovery / Failed Branch Lessons Integration / No-Order Research Branch Selection Pack

PowerShell uygulama adımları
===========================

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628A_new_hypothesis_candidate_discovery_failed_branch_lessons_integration_no_order_research_branch_selection_pack_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436628A_hypothesis_candidate_discovery.py

$env:PYTHONPATH="src"
python tools/check_4B436628A_hypothesis_candidate_discovery.py --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hypothesis_candidate_discovery_4B436628A.py

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Discovery pack çalıştırma
=========================

$latestLedger = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436625X_hyp005_shadow_merged_ledger_*.jsonl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$latestH3 = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436627GH3_hyp005_shadow_stagnation_diagnostics_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$latestH4 = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436627GH4_hyp005_shadow_parameter_sensitivity_matrix_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$latestH5 = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436627GH5_hyp005_r1_branch_review_closure_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python tools/run_4B436628A_hypothesis_candidate_discovery.py `
  --ledger-jsonl $latestLedger.FullName `
  --h3-diagnostics-json $latestH3.FullName `
  --h4-sensitivity-json $latestH4.FullName `
  --h5-closure-json $latestH5.FullName `
  --out-dir .\reports\hyp005_r1_canonical `
  --review-ok

$latest28A = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436628A_new_hypothesis_candidate_discovery_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Get-Content $latest28A.FullName -Raw -Encoding UTF8

Commit
======

git status --short
git add -A
git commit -m "4B.4.3.6.6.28A new hypothesis candidate discovery research pack"
git tag -a 4B.4.3.6.6.28A -m "Accepted new hypothesis candidate discovery research baseline"
git push
git push origin 4B.4.3.6.6.28A

Rollback
========

python tools/rollback_4B436628A_hypothesis_candidate_discovery.py
