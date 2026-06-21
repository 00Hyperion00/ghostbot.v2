4B.4.3.6.6.30P-H3 Submit-Arm Real 30O Evidence Selection Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py --once-json
  python tools/check_4B436630P_H2_submit_arm_direct_30o_evidence_consumption_hotfix.py --once-json
  python tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_submit_arm_preflight_4B436630P.py tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H1.py tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H2.py tests/test_paper_sandbox_submit_arm_preflight_4B436630P_H3.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py --reports-dir .\reports\production_hardening

Expected decision:
  PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL

Commit only if run evidence is READY:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30P-H3 submit-arm real 30O evidence selection hotfix"
  git tag -a 4B.4.3.6.6.30P-H3 -m "Accepted submit-arm real 30O evidence selection hotfix"
  git push origin main
  git push origin 4B.4.3.6.6.30P-H3

Risk posture: submit remains blocked, exchange submit false, live-real false.
