4B.4.3.6.6.30P Paper Sandbox Submit-Arm Preflight

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630P_paper_sandbox_submit_arm_preflight_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630P_paper_sandbox_submit_arm_preflight.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py --once-json
  python tools/check_4B436630O_H6_reconciliation_module_checker_final.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_submit_arm_preflight_4B436630P.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py --reports-dir .\reports\production_hardening

Expected decision:
  PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30P paper sandbox submit-arm preflight"
  git tag -a 4B.4.3.6.6.30P -m "Accepted paper sandbox submit-arm preflight"
  git push origin main
  git push origin 4B.4.3.6.6.30P

Risk posture:
  - Sandbox submit readiness proof only.
  - No exchange submit.
  - No paper sandbox canary submit until 30Q.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
