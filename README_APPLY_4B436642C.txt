4B.4.3.6.6.42C — Paper Sandbox External Runtime Soak Start Handoff Contract

Apply:
  python tools/apply_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436642C_paper_sandbox_external_runtime_soak_start_handoff_contract.py --reports-dir .\reports\recovery --once-json

Safety:
  Soak execution: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
