4B.4.3.6.6.38E — Paper Sandbox Runtime Activation Preflight

Purpose:
- Verify 38D READY source evidence.
- Lock typed operator approval verification for paper sandbox runtime activation preflight.
- Lock local runtime-start preflight contract.
- Keep runtime start, paper order, network order, live-real, exchange submit, private API and signed requests disabled.

Apply:
  python tools/apply_4B436638E_paper_sandbox_runtime_activation_preflight.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436638E_paper_sandbox_runtime_activation_preflight.py --once-json

Tests:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_runtime_activation_preflight_4B436638E.py

Run reports:
  $env:PYTHONPATH="src"
  python tools/run_4B436638E_paper_sandbox_runtime_activation_preflight.py --reports-dir .\reports\recovery --once-json

Expected READY decision:
  PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_READY_TYPED_OPERATOR_APPROVAL_VERIFIED_LOCAL_START_PREFLIGHT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED

This patch does not start paper runtime and does not submit orders.
