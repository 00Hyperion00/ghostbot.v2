4B.4.3.6.6.41B — Paper Sandbox External Runtime Start Handoff Contract

Apply:
  python tools/apply_4B436641B_paper_sandbox_external_runtime_start_handoff_contract.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436641B_paper_sandbox_external_runtime_start_handoff_contract.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436641B_paper_sandbox_external_runtime_start_handoff_contract.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
