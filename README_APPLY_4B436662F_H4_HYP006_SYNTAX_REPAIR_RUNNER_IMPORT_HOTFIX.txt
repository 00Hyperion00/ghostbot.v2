4B.4.3.6.6.62F-H4 HYP006 Syntax Repair / Runner Import Hotfix

Apply:
  python tools/apply_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py --once-json
  python tools/run_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py --reports-dir .\reports\recovery --once-json

Test:
  python -m pytest -q tests/test_full_repo_regression_stabilization_4B436662F_H4.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
