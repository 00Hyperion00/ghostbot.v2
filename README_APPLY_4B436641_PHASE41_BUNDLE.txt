4B.4.3.6.6.41 — Phase 41 No-Order Runtime Soak Bundle

Apply:
  python tools/apply_4B436641_phase41_no_order_runtime_soak_bundle.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436641_phase41_no_order_runtime_soak_bundle.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436641_phase41_no_order_runtime_soak_bundle.py --reports-dir .\reports\recovery --once-json

Test:
  set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  set PYTHONPATH=src
  python -m pytest -q tests/test_phase41_no_order_runtime_soak_bundle_4B436641.py tests/test_paper_sandbox_no_order_runtime_soak_planning_4B436641A.py tests/test_paper_sandbox_external_runtime_start_handoff_contract_4B436641B.py tests/test_paper_sandbox_runtime_presence_evidence_gate_4B436641C.py tests/test_paper_sandbox_no_order_runtime_health_probe_evidence_4B436641D.py tests/test_paper_sandbox_no_order_runtime_metrics_evidence_4B436641E.py tests/test_paper_sandbox_no_order_soak_window_contract_4B436641F.py tests/test_paper_sandbox_runtime_incident_budget_review_4B436641G.py tests/test_paper_sandbox_no_order_soak_acceptance_gate_4B436641H.py tests/test_paper_sandbox_no_order_runtime_soak_closure_4B436641I.py

Safety:
  Runtime start: not performed by patch
  Runtime command execution: not performed
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
