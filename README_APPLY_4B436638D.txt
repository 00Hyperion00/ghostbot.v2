4B.4.3.6.6.38D — Paper Sandbox Operator Approval Ledger

Apply:
  python tools/apply_4B436638D_paper_sandbox_operator_approval_ledger.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436638D_paper_sandbox_operator_approval_ledger.py --once-json

Tests:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_operator_approval_ledger_4B436638D.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run and write reports:
  $env:PYTHONPATH="src"
  python tools/run_4B436638D_paper_sandbox_operator_approval_ledger.py --reports-dir .\reports\recovery --once-json

Expected decision:
  PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_READY_TYPED_APPROVAL_EVIDENCE_OPERATOR_IDENTITY_NO_RUNTIME_START_NO_NETWORK_ORDER_LOCKED

No-submit constraints:
  - no paper runtime start
  - no paper/network order submit
  - no live-real approval
  - no exchange submit approval
  - no network/HTTP/signed request/private account access
  - no training/reload/runtime overlay
  - no git/report destructive mutation
