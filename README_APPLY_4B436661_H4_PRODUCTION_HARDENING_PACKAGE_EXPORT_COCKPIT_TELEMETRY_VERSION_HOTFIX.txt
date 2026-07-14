# 4B.4.3.6.6.61-H4 Production Hardening Package Export / H2 Regression / Cockpit Telemetry Version Hotfix

Amaç: H3 sonrası kalan production_hardening package/module ambiguity, H2/H3 regresyon anahtarları ve cockpit telemetry version export drift problemini fail-closed şekilde düzeltmek.

Bu patch trading davranışı değiştirmez. Paper submit, network order, live-real, private API ve exchange-submit kilitleri kapalı kalır.

Uygulama:

```powershell
python tools/apply_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py
```

Kontrol:

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py --once-json
python tools/run_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py --reports-dir .eportsecovery --once-json
```

Test:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_h4_4B436661_H4.py
python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_4B436661_H1.py tests/test_release_audit_legacy_api_drift_compatibility_v2_4B436661_H2.py tests/test_release_audit_legacy_api_drift_compatibility_h3_4B436661_H3.py
python -m pytest -q
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```
