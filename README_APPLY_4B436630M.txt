4B.4.3.6.6.30M Paper Sandbox Execution Preflight

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630M_paper_sandbox_execution_preflight_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630M_paper_sandbox_execution_preflight.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630M_paper_sandbox_execution_preflight.py --once-json
  python tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_execution_preflight_4B436630M.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default blocked report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630M_paper_sandbox_execution_preflight.py --reports-dir .\reports\production_hardening

Expected default decision:
  PAPER_SANDBOX_EXECUTION_PREFLIGHT_AUTHORIZATION_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Explicit dry-run authorization report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630M_paper_sandbox_execution_preflight.py --reports-dir .\reports\production_hardening --operator-id operator-30m --authorization-token AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT --issue-dry-run-authorization --write-envelope

Expected ready decision:
  PAPER_SANDBOX_EXECUTION_PREFLIGHT_READY_ORDER_ENVELOPE_BUILT_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30M paper sandbox execution preflight"
  git tag -a 4B.4.3.6.6.30M -m "Accepted paper sandbox execution preflight"
  git push origin main
  git push origin 4B.4.3.6.6.30M

Risk posture:
  - Order envelope proof only.
  - No real paper execution.
  - No exchange submit.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
