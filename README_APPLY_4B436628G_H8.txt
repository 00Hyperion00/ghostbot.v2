4B.4.3.6.6.28G-H8 HYP-006 BNBUSDT Overlay Out-of-Sample Evaluation / No-Order Runtime Activation Blocked Decision Pack

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive `
    -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation_runtime_activation_blocked_decision_pack_patch.zip" `
    -DestinationPath . `
    -Force
  python tools/apply_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py

Check/test:
  $env:PYTHONPATH="src"
  python tools/check_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py --once-json

  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_hyp006_bnbusdt_overlay_oos_evaluation_4B436628G_H8.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run report:
  $env:PYTHONPATH="src"
  python tools/run_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py `
    --reports-dir .\reports\hyp006_r1_canonical

Expected safety posture:
  approved_for_bnbusdt_oos_evaluation may be true if latest H7 vs previous H7 passes OOS guards.
  approved_for_runtime_overlay_activation_candidate is always false.
  approved_for_parameter_relaxation_candidate is always false.
  approved_for_paper_candidate is always false.
  approved_for_live_real is always false.
  runtime_overlay_activation_performed is always false.
  trading_action_performed/order_actions_performed are always false.

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.28G-H8 HYP-006 BNBUSDT overlay OOS evaluation"
  git tag -a 4B.4.3.6.6.28G-H8 -m "Accepted HYP-006 BNBUSDT overlay OOS evaluation baseline"
  git push
  git push origin 4B.4.3.6.6.28G-H8
