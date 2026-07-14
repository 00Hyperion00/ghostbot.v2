4B.4.3.6.6.61-H1 Legacy API Drift Compatibility Hotfix

Amaç:
- Full repo pytest collection sonrası kalan 3 legacy API drift import hatasını düzeltmek.
- Eski testleri susturmak yerine public API kontratlarını geriye uyumlu restore etmek.
- No paper submit / no network order / no live / no exchange-submit güvenlik kilitlerini korumak.

Hedef public API export'ları:
- tradebot.paper_sandbox_execution_reconciliation_gate.SQLITE_MIRROR_REQUIRED_DECISION
- tradebot.production_hardening.build_production_hardening_snapshot
- tradebot.operator_cockpit_v2_read_only.OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY

Uygulama:
  python tools/apply_4B436661_H1_legacy_api_drift_compatibility_hotfix.py

Kontrol:
  $env:PYTHONPATH="src"
  python tools/check_4B436661_H1_legacy_api_drift_compatibility_hotfix.py --once-json

Rapor:
  $env:PYTHONPATH="src"
  python tools/run_4B436661_H1_legacy_api_drift_compatibility_hotfix.py --reports-dir .\reports\recovery --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_release_audit_legacy_api_drift_compatibility_4B436661_H1.py
  python -m pytest -q
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
