4B.4.3.6.6.28G-H6 HYP-006 No-Order Filter Shadow Overlay Design / Accepted Candidate Quarantine Review Pack

Purpose:
- Read latest 28G-H5 counterfactual filter candidate ranking report.
- Separate accepted review candidates into primary no-order overlay design and quarantine review-only buckets.
- Preserve explicit do-not-relax blocklist.
- Keep all parameter, paper/live, runtime activation, training, reload, and order gates fail-closed.

Apply:
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design_accepted_candidate_quarantine_review_pack_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py

Check/test:
$env:PYTHONPATH="src"
python tools/check_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_no_order_filter_shadow_overlay_design_4B436628G_H6.py

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run report:
$env:PYTHONPATH="src"
python tools/run_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py `
  --reports-dir .\reports\hyp006_r1_canonical

Expected fail-closed fields:
- approved_for_parameter_relaxation_candidate: False
- approved_for_paper_candidate: False
- approved_for_live_real: False
- runtime_overlay_activation_performed: False
- training_performed: False
- reload_performed: False
- trading_action_performed: False
- order_actions_performed: False

Commit/tag:
git status --short
git add -A
git commit -m "4B.4.3.6.6.28G-H6 HYP-006 no-order filter shadow overlay design"
git tag -a 4B.4.3.6.6.28G-H6 -m "Accepted HYP-006 no-order filter shadow overlay design baseline"
git push
git push origin 4B.4.3.6.6.28G-H6
