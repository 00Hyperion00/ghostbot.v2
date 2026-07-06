4B.4.3.6.6.40A — Paper Sandbox Runtime Start Execution Authorization Review

Apply:
  python tools/apply_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436640A_paper_sandbox_runtime_start_execution_authorization_review.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
