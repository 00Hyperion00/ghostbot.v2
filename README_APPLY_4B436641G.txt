4B.4.3.6.6.41G — Paper Sandbox Runtime Incident Budget Review

Apply:
  python tools/apply_4B436641G_paper_sandbox_runtime_incident_budget_review.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436641G_paper_sandbox_runtime_incident_budget_review.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436641G_paper_sandbox_runtime_incident_budget_review.py --reports-dir .\reports\recovery --once-json

Safety:
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
