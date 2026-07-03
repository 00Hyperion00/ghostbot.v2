4B.4.3.6.6.34B — Evidence Inventory Reconciliation

Apply:
  python tools/apply_4B436634B_evidence_inventory_reconciliation.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634B_evidence_inventory_reconciliation.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_evidence_inventory_reconciliation_4B436634B.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634B_evidence_inventory_reconciliation.py --reports-dir .eportsecovery --once-json

Expected decision:
  EVIDENCE_INVENTORY_RECONCILIATION_READY_POST_34A_BASELINE_LOCKED

Safety:
  Evidence reconciliation only. No report deletion, no file move, no submit, no paper/live approval, no runtime overlay, no training/reload.
