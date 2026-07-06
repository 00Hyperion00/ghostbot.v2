4B.4.3.6.6.42I — Paper Sandbox No-Order Soak Execution Closure

Apply:
  python tools/apply_4B436642I_paper_sandbox_no_order_soak_execution_closure.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436642I_paper_sandbox_no_order_soak_execution_closure.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436642I_paper_sandbox_no_order_soak_execution_closure.py --reports-dir .\reports\recovery --once-json

Safety:
  Soak execution: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
