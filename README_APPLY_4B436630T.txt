4B.4.3.6.6.30T Paper Soak / Evidence Window

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630T_paper_soak_evidence_window_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630T_paper_soak_evidence_window.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630T_paper_soak_evidence_window.py --once-json
  python tools/check_4B436630S_paper_mode_runtime_guardrail.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_soak_evidence_window_4B436630T.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630T_paper_soak_evidence_window.py --reports-dir .eports\production_hardening

Expected ready decision:
  PAPER_SOAK_EVIDENCE_WINDOW_READY_MULTI_CYCLE_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30T paper soak evidence window"
  git tag -a 4B.4.3.6.6.30T -m "Accepted paper soak evidence window"
  git push origin main
  git push origin 4B.4.3.6.6.30T

Risk posture:
  - Consumes latest valid 30S guarded runtime ready report.
  - Runs deterministic multi-cycle paper soak evidence only.
  - Proves cap and kill-switch continuity across the soak window.
  - No order action.
  - No exchange submit.
  - No live-real.
