4B.4.3.6.6.34G — Signature Approval Package

Apply:
  python tools/apply_4B436634G_signature_approval_package.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634G_signature_approval_package.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_signature_approval_package_4B436634G.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634G_signature_approval_package.py --reports-dir .\reports\recovery --once-json

No submit, no unlock, no approval, no file move/delete.
