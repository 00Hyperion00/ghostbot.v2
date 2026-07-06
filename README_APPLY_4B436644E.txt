4B.4.3.6.6.44E — Paper Sandbox Metrics Evidence Acceptance Criteria

Apply:
  python tools/apply_4B436644E_paper_sandbox_metrics_evidence_acceptance_criteria.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436644E_paper_sandbox_metrics_evidence_acceptance_criteria.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436644E_paper_sandbox_metrics_evidence_acceptance_criteria.py --reports-dir .\reports\recovery --once-json

Safety:
  Evidence acceptance: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Runtime health endpoint: not called
  Runtime metrics collection: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
