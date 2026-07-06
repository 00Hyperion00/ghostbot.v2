4B.4.3.6.6.42E — Paper Sandbox Localhost Health Probe Evidence Gate

Apply:
  python tools/apply_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436642E_paper_sandbox_localhost_health_probe_evidence_gate.py --reports-dir .\reports\recovery --once-json

Safety:
  Soak execution: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
