4B.4.3.6.6.34A — Post-Recovery Next Phase Planning

Apply:
  python tools/apply_4B436634A_post_recovery_next_phase_planning.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634A_post_recovery_next_phase_planning.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_post_recovery_next_phase_planning_4B436634A.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634A_post_recovery_next_phase_planning.py --reports-dir .\reports\recovery --once-json

Expected decision:
  POST_RECOVERY_NEXT_PHASE_PLANNING_READY_NO_SUBMIT_BOUNDARY_LOCKED

Safety:
  Planning-only. No submit, no paper/live approval, no runtime overlay, no training/reload, no archive execution, no file move/delete.
