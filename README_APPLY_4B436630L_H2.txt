4B.4.3.6.6.30L-H2 Candidate Unlock Hotfix Checker Compatibility

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630L_H2_candidate_unlock_hotfix_checker_compat_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py --once-json
  python tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py --once-json
  python tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py --once-json
  python tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_candidate_unlock_gate_4B436630L.py tests/test_paper_sandbox_candidate_unlock_gate_4B436630L_H2.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30L-H2 candidate unlock hotfix checker compatibility"
  git tag -a 4B.4.3.6.6.30L-H2 -m "Accepted candidate unlock hotfix checker compatibility"
  git push origin main
  git push origin 4B.4.3.6.6.30L-H2

Risk posture:
  - Candidate-only unlock proof preserved.
  - No real paper execution.
  - No exchange submit.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
