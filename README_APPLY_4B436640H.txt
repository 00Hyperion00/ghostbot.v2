4B.4.3.6.6.40H — Paper Sandbox Observation Runtime Metrics Actual Evidence Gate

Apply:
  python tools/apply_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436640H_paper_sandbox_observation_runtime_metrics_actual_evidence_gate.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
