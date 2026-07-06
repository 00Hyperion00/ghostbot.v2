4B.4.3.6.6.40C — Paper Sandbox Runtime Start Pre-Execution Gate

Apply:
  python tools/apply_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436640C_paper_sandbox_runtime_start_pre_execution_gate.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
