4B.4.3.6.6.28G-H4 HYP-006 Near-Miss Outcome Attribution / Gate-Combo Counterfactual No-Order Research Report Patch

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive `
    -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H4_hyp006_near_miss_outcome_attribution_gate_combo_counterfactual_no_order_research_report_patch.zip" `
    -DestinationPath . `
    -Force
  python tools/apply_4B436628G_H4_hyp006_near_miss_outcome_attribution.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436628G_H4_hyp006_near_miss_outcome_attribution.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_hyp006_near_miss_outcome_attribution_4B436628G_H4.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run report from latest H3 artifact:
  $env:PYTHONPATH="src"
  python tools/run_4B436628G_H4_hyp006_near_miss_outcome_attribution.py `
    --reports-dir .\reports\hyp006_r1_canonical

Optional no-network run using CSV:
  $env:PYTHONPATH="src"
  python tools/run_4B436628G_H4_hyp006_near_miss_outcome_attribution.py `
    --reports-dir .\reports\hyp006_r1_canonical `
    --input-csv .\path\to\candles.csv

Expected safety:
  read_only=True
  counterfactual_research_only=True
  approved_for_parameter_relaxation_candidate=False
  approved_for_paper_candidate=False
  approved_for_live_real=False
  training_performed=False
  reload_performed=False
  trading_action_performed=False
  order_actions_performed=False

Commit after local acceptance:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.28G-H4 HYP-006 near-miss outcome attribution"
  git tag -a 4B.4.3.6.6.28G-H4 -m "Accepted HYP-006 near-miss outcome attribution baseline"
  git push
  git push origin 4B.4.3.6.6.28G-H4
