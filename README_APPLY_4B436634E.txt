4B.4.3.6.6.34E — Transition Approval Dry-Run

Apply:
  python tools/apply_4B436634E_transition_approval_dry_run.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634E_transition_approval_dry_run.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_transition_approval_dry_run_4B436634E.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634E_transition_approval_dry_run.py --reports-dir .eportsecovery --once-json

Expected decision:
  TRANSITION_APPROVAL_DRY_RUN_READY_NO_SUBMIT_HANDOFF_LOCKED

Safety:
  Evidence/dry-run only. No submit, no paper/live approval, no unlock, no runtime overlay, no report deletion, no file movement, no training/reload.
