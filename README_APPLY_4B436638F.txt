4B.4.3.6.6.38F — Paper Sandbox Local Runtime Activation Harness

Scope:
- Source-gates on 4B.4.3.6.6.38E READY evidence.
- Defines a local paper-only runtime activation harness contract.
- Verifies paper-only activation harness policy, local-only activation session ledger, and fail-closed guard.
- Keeps paper transition approval false and blocked.
- Keeps runtime process start, network order, live-real, exchange submit, signed request, private API access disabled.

Apply:
  python tools/apply_4B436638F_paper_sandbox_local_runtime_activation_harness.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436638F_paper_sandbox_local_runtime_activation_harness.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_local_runtime_activation_harness_4B436638F.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436638F_paper_sandbox_local_runtime_activation_harness.py --reports-dir .\reports\recovery --once-json

Safety:
- No runtime start.
- No network order.
- No live-real.
- No exchange submit.
- No HTTP/signed/private API call.
- No training/reload.
- No git mutation.
- No destructive report mutation.
