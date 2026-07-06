4B.4.3.6.6.41A — Paper Sandbox No-Order Runtime Soak Planning

Apply:
  python tools/apply_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
