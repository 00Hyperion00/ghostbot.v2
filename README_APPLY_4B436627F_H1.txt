4B.4.3.6.6.27F-H1
Risk-Percent Position Sizing / Stable Skip-Code Compatibility /
Mandatory Entry-Preflight Fail-Closed / Legacy Test-Double Regression Hotfix

WINDOWS POWERSHELL APPLICATION

1) Go to the current project root:
   cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) Overlay the patch ZIP:
   Expand-Archive `
     -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627F_H1_stable_skip_code_mandatory_entry_preflight_fail_closed_hotfix_patch.zip" `
     -DestinationPath . `
     -Force

3) Apply the hotfix:
   python tools/apply_4B436627F_H1_stable_skip_code_mandatory_entry_preflight_fail_closed.py

4) Run the read-only checker:
   $env:PYTHONPATH="src"
   python tools/check_4B436627F_H1_stable_skip_code_mandatory_entry_preflight_fail_closed.py --once-json

5) Run the focused regression matrix:
   $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
   $env:PYTHONPATH="src"
   python -m pytest -q `
     tests/test_risk_percent_position_sizing_4B436627F_H1.py `
     tests/test_risk_percent_position_sizing_4B436627F.py `
     tests/test_config_profile_safety.py `
     tests/test_risk_guards.py `
     tests/test_entry_lifecycle_guard.py `
     tests/test_exit_lifecycle_guard.py `
     tests/test_execution_hygiene.py `
     tests/test_live_demo_order_lifecycle_hardening.py

6) Run the previous 27A-27E security chain:
   python -m pytest -q `
     tests/test_binance_environment_router_4B436627A.py `
     tests/test_execution_policy_gate_4B436627B.py `
     tests/test_truthful_order_preflight_4B436627C.py `
     tests/test_binance_demo_authenticated_no_order_preflight_probe_4B436627CH1.py `
     tests/test_ai_startup_reload_threshold_parity_4B436627E.py

7) Compile all Python files:
   python -m compileall -q src tools tests

ROLLBACK

python tools/rollback_4B436627F_H1_stable_skip_code_mandatory_entry_preflight_fail_closed.py

SAFETY NOTES

- Patch application does not mutate configuration.
- Patch application does not mutate the scheduler.
- Patch application does not trigger training or reload.
- Patch application does not perform network requests.
- Patch application does not place orders.
- Paper/live order enablement remains disabled.
