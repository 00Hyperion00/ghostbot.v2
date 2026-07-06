4B.4.3.6.6.42B — Paper Sandbox Typed No-Order Soak Execution Approval

Apply:
  python tools/apply_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436642B_paper_sandbox_typed_no_order_soak_execution_approval.py --reports-dir .\reports\recovery --once-json

Safety:
  Soak execution: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
