4B.4.3.6.6.42F — Paper Sandbox No-Order Runtime Metrics Evidence Collection Gate

Apply:
  python tools/apply_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436642F_paper_sandbox_no_order_runtime_metrics_evidence_collection_gate.py --reports-dir .\reports\recovery --once-json

Safety:
  Soak execution: not performed by patch
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
