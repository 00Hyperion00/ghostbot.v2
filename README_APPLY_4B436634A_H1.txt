4B.4.3.6.6.34A-H1 — Source 33I Completion Gate Hotfix

Apply:
  python tools/apply_4B436634A_H1_source_33i_gate_hotfix.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634A_H1_source_33i_gate_hotfix.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_post_recovery_next_phase_planning_h1_4B436634A_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634A_H1_source_33i_gate_hotfix.py --reports-dir .\reports\recovery --once-json

Then re-check 34A:
  python tools/check_4B436634A_post_recovery_next_phase_planning.py --once-json
  python tools/run_4B436634A_post_recovery_next_phase_planning.py --reports-dir .\reports\recovery --once-json

Expected H1 decision:
  SOURCE_33I_COMPLETION_GATE_HOTFIX_READY

Expected 34A decision:
  POST_RECOVERY_NEXT_PHASE_PLANNING_READY_NO_SUBMIT_BOUNDARY_LOCKED
