4B.4.3.6.6.27G
Risk-Sizing Runtime Telemetry / Operator Cockpit Audit Parity / Fail-Closed Evidence Export Gate

PowerShell uygulama adımları
===========================

1) Proje klasörüne geçin:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) ZIP dosyasını açın:

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627G_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity_fail_closed_evidence_export_gate_patch.zip" `
  -DestinationPath . `
  -Force

3) Patch'i uygulayın:

python tools/apply_4B436627G_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity.py

4) Read-only checker:

$env:PYTHONPATH="src"
python tools/check_4B436627G_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity.py --once-json

5) Hedefli testler:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q `
  tests/test_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity_4B436627G.py `
  tests/test_operator_cockpit_v2_read_only_dashboard_shell_4B436626A.py `
  tests/test_operator_cockpit_v2_safe_operator_actions_4B436626C.py `
  tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py `
  tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py `
  tests/test_operator_cockpit_v2_evidence_pack_preflight_timeout_hotfix_4B436626DH2H2.py `
  tests/test_risk_percent_position_sizing_4B436627F_H1.py `
  tests/test_risk_percent_position_sizing_4B436627F.py

6) Önceki güvenlik zinciri:

python -m pytest -q `
  tests/test_binance_environment_router_4B436627A.py `
  tests/test_execution_policy_gate_4B436627B.py `
  tests/test_truthful_order_preflight_4B436627C.py `
  tests/test_binance_demo_authenticated_no_order_preflight_probe_4B436627CH1.py `
  tests/test_ai_startup_reload_threshold_parity_4B436627E.py

7) Derleme kontrolü:

# Tarihsel backup ve legacy patch arşivleri aktif kod değildir.
# Aktif kaynak ağacını gereksiz gecikme olmadan derleyin:
python -m compileall -q -x '(_patch_backup|legacy_patches)' src tools tests

Geri alma
=========

python tools/rollback_4B436627G_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity.py

Notlar
=====

- Patch config değiştirmez.
- Scheduler değiştirmez.
- Training veya reload çalıştırmaz.
- Emir göndermez.
- Paper/live yetkisi açmaz.
- Legacy evidence pack rotası korunur.
- Yeni risk-sizing evidence ZIP rotası, runtime sizing kanıtı eksikse HTTP 412 ile fail-closed engellenir.

Beklenen test özetleri
======================

- 27G hedefli ve cockpit uyumluluk matrisi: 68 passed
- Operator Cockpit V2 ailesi: 88 passed
- 27F-H1 risk/lifecycle matrisi: 60 passed
- 27A-27E güvenlik zinciri: 56 passed
