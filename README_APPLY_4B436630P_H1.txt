4B.4.3.6.6.30P-H1 Submit-Arm 30O-H6 Source Consumption Hotfix

Problem:
  30P checker passed with synthetic direct 30O payload, but real evidence run produced:
  PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_30O_RECONCILIATION_PROOF_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL
  because 30O-H6 reconciliation proof can be nested inside checker/evidence summaries.

Scope:
  - Normalize direct 30O reports and nested 30O-H6 target_30o_report_summary payloads.
  - Keep submit blocked.
  - Keep exchange submit blocked.
  - Keep live-real blocked.

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix.py --once-json
  python tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_submit_arm_preflight_4B436630P.py tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py --reports-dir .\reports\production_hardening

Expected decision:
  PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30P-H1 submit-arm 30O-H6 source consumption hotfix"
  git tag -a 4B.4.3.6.6.30P-H1 -m "Accepted submit-arm 30O-H6 source consumption hotfix"
  git push origin main
  git push origin 4B.4.3.6.6.30P-H1
