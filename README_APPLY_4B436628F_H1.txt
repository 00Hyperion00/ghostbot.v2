4B.4.3.6.6.28F-H1 Operator Cockpit HYP-006 Dashboard Seed Binding / Legacy HYP-005 Panel Suppression / Active Research Branch Display Parity Hotfix

APPLY
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628F_H1_operator_cockpit_hyp006_dashboard_seed_binding_legacy_hyp005_suppression_active_branch_display_parity_hotfix_patch.zip" -DestinationPath . -Force
python tools/apply_4B436628F_H1_operator_cockpit_hyp006_binding.py

CHECK
$env:PYTHONPATH="src"
python tools/check_4B436628F_H1_operator_cockpit_hyp006_binding.py --once-json

TEST
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_operator_cockpit_hyp006_binding_4B436628F_H1.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

OPERATOR COCKPIT RESTART
Close the current Operator Cockpit window and start it again:
python tools/run_operator_cockpit_v2_desktop_4B436626D.py --allow-browser-fallback

EXPECTED UI
Model ve Strateji panelinde:
Branch    : HYP-006-R1
Namespace : HYP006_R1
Durum     : HYP006_NO_MODEL_RELOAD_READ_ONLY

Risk gates:
Paper/live/order/training/reload remain closed.

COMMIT

git status --short
git add -A
git commit -m "4B.4.3.6.6.28F-H1 Operator Cockpit HYP-006 binding parity hotfix"
git tag -a 4B.4.3.6.6.28F-H1 -m "Accepted Operator Cockpit HYP-006 binding parity hotfix baseline"
git push
git push origin 4B.4.3.6.6.28F-H1
