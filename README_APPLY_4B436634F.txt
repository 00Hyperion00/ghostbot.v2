4B.4.3.6.6.34F — Operator Signature Validation

Apply:
  python tools/apply_4B436634F_operator_signature_validation.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634F_operator_signature_validation.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_operator_signature_validation_4B436634F.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634F_operator_signature_validation.py --reports-dir .eportsecovery --once-json

Expected decision:
  OPERATOR_SIGNATURE_VALIDATION_READY_NO_SUBMIT_APPROVAL_LOCKED

Optional dry-run signature validation:
  python tools/check_4B436634F_operator_signature_validation.py --signature-file .\operator_signature_34F.json --once-json

Safety:
  Evidence/dry-run only. No submit, no paper/live approval, no unlock, no runtime overlay, no report deletion, no file movement, no training/reload.
