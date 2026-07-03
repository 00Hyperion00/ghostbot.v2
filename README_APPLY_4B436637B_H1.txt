4B.4.3.6.6.37B-H1 Install Contract Launcher Alignment Hotfix

Apply:
  python tools/apply_4B436637B_H1_install_contract_launcher_alignment_hotfix.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436637B_H1_install_contract_launcher_alignment_hotfix.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_install_contract_launcher_alignment_hotfix_4B436637B_H1.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436637B_H1_install_contract_launcher_alignment_hotfix.py --reports-dir .\reports\recovery --once-json

Expected decision:
  INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_HOTFIX_READY_NO_SUBMIT_P0_1_CLOSED
