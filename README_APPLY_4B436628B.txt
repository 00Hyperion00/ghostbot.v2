4B.4.3.6.6.28B — HYP-006-R1 Candidate Spec Draft / No-Order Shadow Registration Gate

Apply:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628B_hyp006_r1_candidate_spec_draft_no_order_shadow_registration_gate_fail_closed_research_activation_pack_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436628B_hyp006_candidate_spec_registration.py

Check:

$env:PYTHONPATH="src"
python tools/check_4B436628B_hyp006_candidate_spec_registration.py --once-json

Test:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_candidate_spec_registration_4B436628B.py

Compile:

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run 28B pack:

$latest28A = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436628A_new_hypothesis_candidate_discovery_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

New-Item -ItemType Directory -Force .\reports\hyp006_r1_candidate_spec | Out-Null

python tools/run_4B436628B_hyp006_candidate_spec_registration.py `
  --discovery-json $latest28A.FullName `
  --out-dir .\reports\hyp006_r1_candidate_spec `
  --review-ok

Read latest 28B report:

$latest28B = Get-ChildItem `
  .\reports\hyp006_r1_candidate_spec\4B436628B_hyp006_r1_candidate_spec_registration_gate_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Get-Content $latest28B.FullName -Raw -Encoding UTF8

Commit after clean checks:

git status --short
git add -A
git commit -m "4B.4.3.6.6.28B HYP-006-R1 candidate spec no-order registration gate"
git tag -a 4B.4.3.6.6.28B -m "Accepted HYP-006-R1 candidate spec no-order registration gate baseline"
git push
git push origin 4B.4.3.6.6.28B

Rollback:

python tools/rollback_4B436628B_hyp006_candidate_spec_registration.py

Safety: 28B does not start shadow collection, paper/live, training, reload, scheduler mutation, or order execution. 28C is required before any no-order runner dry-run registration.
