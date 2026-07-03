4B.4.3.6.6.34D — Operator Decision Token

Apply:
  python tools/apply_4B436634D_operator_decision_token.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634D_operator_decision_token.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_operator_decision_token_4B436634D.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634D_operator_decision_token.py --reports-dir .eportsecovery --once-json

Expected decision:
  OPERATOR_DECISION_TOKEN_READY_FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED

Safety:
  Evidence/dry-run only. No submit, no paper/live approval, no unlock, no runtime overlay, no report deletion, no file movement, no training/reload.
