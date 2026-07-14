4B.4.3.6.6.61-H5 Production Hardening Import Finalization / H4 Report Predicate Fix

Apply:
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436661_H5_production_hardening_import_finalization_h4_predicate_fix_patch.zip" -DestinationPath . -Force
python tools/apply_4B436661_H5_production_hardening_import_finalization_h4_predicate_fix.py

Check:
$env:PYTHONPATH="src"
python tools/check_4B436661_H5_production_hardening_import_finalization_h4_predicate_fix.py --once-json

Run:
python tools/run_4B436661_H5_production_hardening_import_finalization_h4_predicate_fix.py --reports-dir .\reports\recovery --once-json

Tests:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_h5_4B436661_H5.py
python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_4B436661_H1.py tests/test_release_audit_legacy_api_drift_compatibility_v2_4B436661_H2.py tests/test_release_audit_legacy_api_drift_compatibility_h3_4B436661_H3.py tests/test_release_audit_legacy_api_drift_compatibility_h4_4B436661_H4.py tests/test_release_audit_legacy_api_drift_compatibility_h5_4B436661_H5.py
python -m pytest -q
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
