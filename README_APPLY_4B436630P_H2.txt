4B.4.3.6.6.30P-H2 Submit-Arm Direct 30O Evidence Consumption Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py --once-json
  python tools/check_4B436630P_H1_submit_arm_30o_h6_source_consumption_hotfix.py --once-json
  python tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_submit_arm_preflight_4B436630P.py tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H1.py tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H2.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py --reports-dir .\reports\production_hardening

Expected decision:
  PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30P-H2 submit-arm direct 30O evidence consumption hotfix"
  git tag -a 4B.4.3.6.6.30P-H2 -m "Accepted submit-arm direct 30O evidence consumption hotfix"
  git push origin main
  git push origin 4B.4.3.6.6.30P-H2

Risk posture: submit still blocked, exchange submit blocked, live-real blocked.
