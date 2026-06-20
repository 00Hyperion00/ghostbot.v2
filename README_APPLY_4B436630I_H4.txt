4B.4.3.6.6.30I-H4 Internal Execution Harness Repo Hygiene Cleanup

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py --once-json
  python tools/check_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H4.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Manual git hygiene check:
  git ls-files -- _patch_backup tools/_patch_backup tests/_patch_backup docs/_patch_backup

Expected: no output.

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30I-H4 internal execution harness repo hygiene cleanup"
  git tag -a 4B.4.3.6.6.30I-H4 -m "Accepted internal execution harness repo hygiene cleanup"
  git push origin main
  git push origin 4B.4.3.6.6.30I-H4

This patch only removes tracked patch backup artifacts and preserves 30I-H3 acceptance. It does not enable exchange submit, real paper execution, paper candidate, runtime overlays, strategy mutation, training/reload, or live-real.
