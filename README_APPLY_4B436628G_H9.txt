4B.4.3.6.6.28G-H9 HYP006-R1 Fresh Shadow Cycle OOS Delta Review

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_hyp006_fresh_shadow_cycle_oos_delta_review_4B436628G_H9.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run H4-H8 chain and H9 aggregation:
  $env:PYTHONPATH="src"
  python tools/run_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py `
    --reports-dir .\reports\hyp006_r1_canonical `
    --fresh-h3-stamp 20260619T210504Z `
    --run-h4-h8-chain

Run H9 aggregation only:
  $env:PYTHONPATH="src"
  python tools/run_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py `
    --reports-dir .\reports\hyp006_r1_canonical `
    --fresh-h3-stamp 20260619T210504Z

Expected accepted decision:
  HYP006_R1_FRESH_SHADOW_CYCLE_OOS_DELTA_REVIEW_READY_PAPER_TRANSITION_STILL_BLOCKED

Hard blocks:
  approved_for_paper_transition_candidate=False
  approved_for_paper_candidate=False
  approved_for_live_real=False
  trading_action_performed=False
