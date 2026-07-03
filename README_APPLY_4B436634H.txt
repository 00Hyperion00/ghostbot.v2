4B.4.3.6.6.34H — Signature Package Closure

Apply:
  python tools/apply_4B436634H_signature_package_closure.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436634H_signature_package_closure.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_signature_package_closure_4B436634H.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436634H_signature_package_closure.py --reports-dir .\reports\recovery --once-json

No submit, no unlock, no approval, no file move/delete.
