4B.4.3.6.6.43 — Phase 43 No-Order Soak Evidence Collection Bundle

Apply:
  python tools/apply_4B436643_phase43_no_order_soak_evidence_collection_bundle.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436643_phase43_no_order_soak_evidence_collection_bundle.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436643_phase43_no_order_soak_evidence_collection_bundle.py --reports-dir .\reports\recovery --once-json

Test:
  set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  set PYTHONPATH=src
  python -m pytest -q tests/test_phase43_no_order_soak_evidence_collection_bundle_4B436643.py

Safety:
  Runtime start: not performed by patch
  Evidence collection: not performed by patch
  Health endpoint call: not performed by patch
  Runtime metrics collection: not performed by patch
  Paper order submit: not performed
  Network order submit: not performed
  Live-real: not approved
  Exchange submit: not performed
