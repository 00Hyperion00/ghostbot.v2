4B.4.3.6.6.40E — Paper Sandbox Controlled Runtime Start Command Package

Apply:
  python tools/apply_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436640E_paper_sandbox_controlled_runtime_start_command_package.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
