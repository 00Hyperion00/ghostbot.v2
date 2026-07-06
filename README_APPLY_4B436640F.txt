4B.4.3.6.6.40F — Paper Sandbox Local Runtime Process Start Evidence

Apply:
  python tools/apply_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436640F_paper_sandbox_local_runtime_process_start_evidence.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
