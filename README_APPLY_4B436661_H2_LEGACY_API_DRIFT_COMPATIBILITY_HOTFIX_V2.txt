4B.4.3.6.6.61-H2 Legacy API Drift Compatibility Hotfix V2

Amaç:
- 61-H1 sonrası kalan full repo pytest collection hatalarını düzeltmek.
- build_production_hardening_snapshot(project_root=...) signature uyumluluğunu restore etmek.
- production_hardening module/package import/export path uyumluluğunu sağlamak.
- OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED public export'unu eklemek.
- 61-H1 testini de geçer hale getirmek.
- No paper submit / no network order / no live / no exchange-submit güvenlik kilitlerini korumak.

Uygulama:
  python tools/apply_4B436661_H2_legacy_api_drift_compatibility_hotfix_v2.py

Kontrol:
  $env:PYTHONPATH="src"
  python tools/check_4B436661_H2_legacy_api_drift_compatibility_hotfix_v2.py --once-json

Rapor:
  $env:PYTHONPATH="src"
  python tools/run_4B436661_H2_legacy_api_drift_compatibility_hotfix_v2.py --reports-dir .\reports\recovery --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_v2_4B436661_H2.py
  python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_4B436661_H1.py
  python -m pytest -q
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
