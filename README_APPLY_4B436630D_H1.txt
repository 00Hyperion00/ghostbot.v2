4B.4.3.6.6.30D-H1 Operator Approval Evidence Capture Settings Clone Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py --once-json
  python tools/check_4B436630D_operator_approval_evidence_capture.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_transition_approval_evidence_capture_4B436630D.py tests/test_paper_transition_approval_evidence_capture_4B436630D_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436630D_operator_approval_evidence_capture.py --reports-dir .\reports\production_hardening
  python tools/run_4B436630D_operator_approval_evidence_capture.py --reports-dir .\reports\production_hardening --operator-id operator-30d --confirmation-token CONFIRM_PAPER_TRANSITION_CANDIDATE --freeze-token FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE --issue-approval --freeze-runtime-envelope --verify-final-risk-cap

This hotfix removes the non-Settings field paper_live_order_enablement_present from the Settings clone constructor. It does not enable paper orders or live-real.
