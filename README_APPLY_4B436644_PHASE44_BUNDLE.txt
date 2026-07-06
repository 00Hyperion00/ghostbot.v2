4B.4.3.6.6.44 — Phase 44 No-Order Soak Evidence Acceptance Bundle

Apply:
  python tools/apply_4B436644_phase44_no_order_soak_evidence_acceptance_bundle.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436644_phase44_no_order_soak_evidence_acceptance_bundle.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436644_phase44_no_order_soak_evidence_acceptance_bundle.py --reports-dir .\reports\recovery --once-json

Test:
  set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  set PYTHONPATH=src
  python -m pytest -q tests/test_phase44_no_order_soak_evidence_acceptance_bundle_4B436644.py

Safety:
  Runtime start: not performed by patch
  Evidence acceptance: not performed by patch
  Evidence collection: not performed by patch
  Health endpoint call: not performed by patch
  Runtime metrics collection: not performed by patch
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
