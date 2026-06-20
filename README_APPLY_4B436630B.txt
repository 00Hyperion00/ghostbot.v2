4B.4.3.6.6.30B Paper Transition Operator Approval Gate

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630B_paper_transition_operator_approval_gate_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630B_paper_transition_operator_approval_gate.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630B_paper_transition_operator_approval_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_transition_operator_gate_4B436630B.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run default review-only report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630B_paper_transition_operator_approval_gate.py --reports-dir .\reports\production_hardening

Default expected decision:
  PAPER_TRANSITION_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED

This patch does not enable paper orders or live-real.
