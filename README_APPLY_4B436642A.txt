4B.4.3.6.6.42A — Paper Sandbox No-Order Soak Execution Authorization Review

Apply:
  python tools/apply_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436642A_paper_sandbox_no_order_soak_execution_authorization_review.py --reports-dir .\reports\recovery --once-json

Safety:
  Soak execution: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
