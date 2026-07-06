4B.4.3.6.6.40B — Paper Sandbox Typed Runtime Start Operator Approval

Apply:
  python tools/apply_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436640B_paper_sandbox_typed_runtime_start_operator_approval.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
