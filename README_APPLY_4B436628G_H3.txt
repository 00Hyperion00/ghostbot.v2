4B.4.3.6.6.28G-H3 HYP-006 Runtime Candidate Scan Hook / Gate-Level Near-Miss Emission Patch

Scope:
- Read-only runtime candidate scan hook for HYP-006-R1.
- Adds gate-level candidate, near-miss, trigger diagnostics in the HYP-006 scan loop.
- Emits 4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss_*.json/md during canonical 28D shadow cycle bundle writes.
- Does not change strategy thresholds, config, scheduler, training, reload, paper/live, or order behavior.

Apply:
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H3_hyp006_runtime_candidate_scan_hook_gate_level_near_miss_emission_patch.zip" `
  -DestinationPath . `
  -Force
python tools/apply_4B436628G_H3_hyp006_runtime_candidate_scan_hook.py

Check:
$env:PYTHONPATH="src"
python tools/check_4B436628G_H3_hyp006_runtime_candidate_scan_hook.py --once-json

Test:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_runtime_candidate_scan_hook_4B436628G_H3.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

After next canonical scheduler run, inspect latest H3 artifact:
$env:PYTHONPATH="src"
python tools/run_4B436628G_H3_hyp006_runtime_candidate_scan_hook.py --reports-dir .\reports\hyp006_r1_canonical

Commit:
git status --short
git add -A
git commit -m "4B.4.3.6.6.28G-H3 HYP-006 runtime candidate scan hook"
git tag -a 4B.4.3.6.6.28G-H3 -m "Accepted HYP-006 runtime candidate scan hook baseline"
git push
git push origin 4B.4.3.6.6.28G-H3
