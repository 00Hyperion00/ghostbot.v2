4B.4.3.6.6.28G-H5
HYP-006 Counterfactual Filter Candidate Ranking / No-Order Gate-Combo Review Pack

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive `
    -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking_no_order_gate_combo_review_pack_patch.zip" `
    -DestinationPath . `
    -Force
  python tools/apply_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py

Check and test:
  $env:PYTHONPATH="src"
  python tools/check_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py --once-json

  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_hyp006_counterfactual_filter_candidate_ranking_4B436628G_H5.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run report:
  $env:PYTHONPATH="src"
  python tools/run_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py `
    --reports-dir .\reports\hyp006_r1_canonical

Expected outputs:
  reports\hyp006_r1_canonical\4B436628G_H5_hyp006_r1_counterfactual_filter_candidate_ranking_*.json
  reports\hyp006_r1_canonical\4B436628G_H5_hyp006_r1_counterfactual_filter_candidate_ranking_*.md

Hard guardrails:
  - No strategy parameter mutation
  - No config mutation
  - No scheduler mutation
  - No training/reload
  - No paper/live/order enablement
  - approved_for_parameter_relaxation_candidate remains False
  - approved_for_paper_candidate remains False
  - approved_for_live_real remains False

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.28G-H5 HYP-006 counterfactual filter candidate ranking"
  git tag -a 4B.4.3.6.6.28G-H5 -m "Accepted HYP-006 counterfactual filter candidate ranking baseline"
  git push
  git push origin 4B.4.3.6.6.28G-H5
