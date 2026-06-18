4B.4.3.6.6.28G-H7 HYP-006 No-Order Overlay Simulation / BNBUSDT Primary Filter Shadow Measurement Pack

Purpose:
- Read latest 28G-H6 no-order filter shadow overlay design report.
- Measure BNBUSDT primary symbol overlay candidate in no-order research mode only.
- Exclude quarantine, watchlist, rejected, and do-not-relax blocklist rows from primary measurement.
- Keep runtime activation, parameter relaxation, paper/live, training, reload, scheduler, and order gates fail-closed.

Apply:
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt_primary_filter_shadow_measurement_pack_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py

Check/test:
$env:PYTHONPATH="src"
python tools/check_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_hyp006_no_order_overlay_simulation_bnbusdt_4B436628G_H7.py

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run report:
$env:PYTHONPATH="src"
python tools/run_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py `
  --reports-dir .\reports\hyp006_r1_canonical

Expected fail-closed fields:
- approved_for_overlay_shadow_measurement: True may be allowed
- approved_for_runtime_overlay_activation_candidate: False
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
git commit -m "4B.4.3.6.6.28G-H7 HYP-006 no-order overlay simulation BNBUSDT"
git tag -a 4B.4.3.6.6.28G-H7 -m "Accepted HYP-006 no-order overlay simulation BNBUSDT baseline"
git push
git push origin 4B.4.3.6.6.28G-H7
