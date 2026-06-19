4B.4.3.6.6.29E-H1 Production Readiness Evidence Refresh / Patch Payload Cleanup

Apply:
  python tools/apply_4B436629E_H1_production_readiness_evidence_refresh.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436629E_H1_production_readiness_evidence_refresh.py --once-json
  python tools/check_4B436629E_production_readiness_consolidation_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_production_readiness_evidence_refresh_4B436629E_H1.py tests/test_production_readiness_consolidation_gate_4B436629E.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence report:
  python tools/run_4B436629E_H1_production_readiness_evidence_refresh.py --reports-dir .\reports\production_hardening

Expected decision:
  PRODUCTION_READINESS_EVIDENCE_REFRESH_READY_LIVE_REAL_STILL_BLOCKED

Commit:
  git add -A
  git commit -m "4B.4.3.6.6.29E-H1 production readiness evidence refresh"
  git tag -a 4B.4.3.6.6.29E-H1 -m "Accepted production readiness evidence refresh hotfix"
  git push
  git push origin 4B.4.3.6.6.29E-H1
