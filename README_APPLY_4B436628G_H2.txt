4B.4.3.6.6.28G-H2
HYP-006 Candidate / Near-Miss Scan Instrumentation
No-Order Research Diagnostics Patch

Purpose
- Add read-only HYP-006 candidate/near-miss instrumentation diagnostics.
- Summarize raw candidate/near-miss/trigger/gate JSON artifacts when present.
- Fall back to latest 28G/28G-H1 blockers if raw candidate scan artifacts are absent.
- Do not mutate config, scheduler, strategy parameters, model state, paper/live mode, or orders.

Apply
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H2_hyp006_candidate_near_miss_scan_instrumentation_no_order_research_diagnostics_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py

Check
$env:PYTHONPATH="src"
python tools/check_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py --once-json

Test
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_candidate_near_miss_instrumentation_4B436628G_H2.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run diagnostic
$env:PYTHONPATH="src"
python tools/run_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py `
  --reports-dir .\reports\hyp006_r1_canonical `
  --out-dir .\reports\hyp006_r1_canonical

Expected outputs
reports\hyp006_r1_canonical\4B436628G_H2_hyp006_r1_candidate_near_miss_scan_instrumentation_*.json
reports\hyp006_r1_canonical\4B436628G_H2_hyp006_r1_candidate_near_miss_scan_instrumentation_*.md

Commit

git status --short
git add -A
git commit -m "4B.4.3.6.6.28G-H2 HYP-006 candidate near-miss instrumentation"
git tag -a 4B.4.3.6.6.28G-H2 -m "Accepted HYP-006 candidate near-miss instrumentation baseline"
git push
git push origin 4B.4.3.6.6.28G-H2

Risk
- No paper.
- No live.
- No training.
- No reload.
- No order.
- No parameter relaxation.
