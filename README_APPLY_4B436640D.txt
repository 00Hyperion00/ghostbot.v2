4B.4.3.6.6.40D — Paper Sandbox Single Instance Runtime Lock Validation

Apply:
  python tools/apply_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436640D_paper_sandbox_single_instance_runtime_lock_validation.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
