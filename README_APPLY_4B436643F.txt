4B.4.3.6.6.43F — Paper Sandbox Incident Budget Evidence Review

Apply:
  python tools/apply_4B436643F_paper_sandbox_incident_budget_evidence_review.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436643F_paper_sandbox_incident_budget_evidence_review.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436643F_paper_sandbox_incident_budget_evidence_review.py --reports-dir .\reports\recovery --once-json

Safety:
  Evidence collection: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Runtime health endpoint: not called
  Runtime metrics collection: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
