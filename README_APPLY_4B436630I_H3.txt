4B.4.3.6.6.30I-H3 Internal Execution Harness Deterministic Acceptance Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py --once-json
  python tools/check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py --once-json
  python tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py --once-json
  python tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I.py tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H2.py tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H3.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

This hotfix stabilizes acceptance checks only. It does not enable exchange submit, real paper execution, paper candidate, runtime overlays, strategy mutation, training/reload, or live-real.
