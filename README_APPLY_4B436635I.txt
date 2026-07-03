4B.4.3.6.6.35I — Phase-35 Final Tag Audit

Apply:
  python tools/apply_4B436635I_phase_35_final_tag_audit.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436635I_phase_35_final_tag_audit.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_phase_35_final_tag_audit_4B436635I.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436635I_phase_35_final_tag_audit.py --reports-dir .\reports\recovery --once-json

Precondition:
  35H must be committed, tagged and pushed. This patch verifies remote tags 35A-35H on origin.
