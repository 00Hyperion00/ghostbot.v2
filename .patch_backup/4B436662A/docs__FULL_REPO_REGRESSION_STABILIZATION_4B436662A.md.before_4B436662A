# 4B.4.3.6.6.62A Full Repo Regression Stabilization / API App Factory / Legacy Contract Sweep

Apply:
python tools/apply_4B436662A_full_repo_regression_stabilization.py

Check:
$env:PYTHONPATH="src"
python tools/check_4B436662A_full_repo_regression_stabilization.py --once-json

Run:
python tools/run_4B436662A_full_repo_regression_stabilization.py --reports-dir .\reports\recovery --once-json

Test:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_full_repo_regression_stabilization_4B436662A.py
python -m pytest -q
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
