4B.4.3.6.6.38B — Paper Sandbox Runtime Preflight

Scope:
- Paper-only runtime config validation.
- No live, no exchange submit, no network order.
- Static preflight only: no runtime start, no network, no order, no paper approval.

Apply:
  python tools/apply_4B436638B_paper_sandbox_runtime_preflight.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436638B_paper_sandbox_runtime_preflight.py --once-json

Test:
  set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  set PYTHONPATH=src
  python -m pytest -q tests/test_paper_sandbox_runtime_preflight_4B436638B.py
  python -m compileall -q -x "(_patch_backup|_patch_payload|legacy_patches)" src tools tests

Run:
  set PYTHONPATH=src
  python tools/run_4B436638B_paper_sandbox_runtime_preflight.py --reports-dir .\reports\recovery --once-json

Expected decision:
  PAPER_SANDBOX_RUNTIME_PREFLIGHT_READY_PAPER_ONLY_NO_LIVE_NO_EXCHANGE_SUBMIT_NO_NETWORK_ORDER_LOCKED
