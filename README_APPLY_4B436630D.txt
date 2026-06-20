4B.4.3.6.6.30D Operator Approval Evidence Capture

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630D_operator_approval_evidence_capture_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630D_operator_approval_evidence_capture.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630D_operator_approval_evidence_capture.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_transition_approval_evidence_capture_4B436630D.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default blocked run:
  python tools/run_4B436630D_operator_approval_evidence_capture.py --reports-dir .\reports\production_hardening

Explicit evidence-capture run:
  python tools/run_4B436630D_operator_approval_evidence_capture.py --reports-dir .\reports\production_hardening --operator-id operator-30d --confirmation-token CONFIRM_PAPER_TRANSITION_CANDIDATE --freeze-token FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE --issue-approval --freeze-runtime-envelope --verify-final-risk-cap

This patch does not enable paper orders, runtime overlays, training/reload, or live-real.
