# 4B.4.3.6.6.62B Full Repo Regression Stabilization Follow-up / Residual Failure Sweep

Apply:
python tools/apply_4B436662B_full_repo_regression_stabilization_residual_sweep.py

Check:
$env:PYTHONPATH="src"
python tools/check_4B436662B_full_repo_regression_stabilization_residual_sweep.py --once-json

Run:
python tools/run_4B436662B_full_repo_regression_stabilization_residual_sweep.py --reports-dir .\reports\recovery --once-json

Test:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_full_repo_regression_stabilization_4B436662B.py
python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_4B436661_H1.py tests/test_release_audit_legacy_api_drift_compatibility_v2_4B436661_H2.py tests/test_release_audit_legacy_api_drift_compatibility_h3_4B436661_H3.py tests/test_release_audit_legacy_api_drift_compatibility_h4_4B436661_H4.py tests/test_release_audit_legacy_api_drift_compatibility_h5_4B436661_H5.py tests/test_release_audit_legacy_api_drift_compatibility_h6_4B436661_H6.py tests/test_release_audit_legacy_api_drift_compatibility_h7_4B436661_H7.py tests/test_full_repo_regression_stabilization_4B436662A.py tests/test_full_repo_regression_stabilization_4B436662B.py
python -m pytest -q
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

No paper submit, no network order, no live, no exchange-submit.
