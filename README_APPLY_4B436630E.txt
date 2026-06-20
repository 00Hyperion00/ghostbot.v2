4B.4.3.6.6.30E Paper Transition Review Re-run

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630E_paper_transition_review_rerun_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630E_paper_transition_review_rerun.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630E_paper_transition_review_rerun.py --once-json
  python tools/check_4B436630D_operator_approval_evidence_capture.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_transition_review_rerun_4B436630E.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436630E_paper_transition_review_rerun.py --reports-dir .\reports\production_hardening

Expected if the 30D ready evidence exists:
  PAPER_TRANSITION_REVIEW_RERUN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED

This patch does not enable paper orders, runtime overlays, training/reload, or live-real.
