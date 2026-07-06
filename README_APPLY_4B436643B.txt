4B.4.3.6.6.43B — Paper Sandbox External Runtime Presence Evidence Collection Handoff

Apply:
  python tools/apply_4B436643B_paper_sandbox_external_runtime_presence_evidence_collection_handoff.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436643B_paper_sandbox_external_runtime_presence_evidence_collection_handoff.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436643B_paper_sandbox_external_runtime_presence_evidence_collection_handoff.py --reports-dir .\reports\recovery --once-json

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
