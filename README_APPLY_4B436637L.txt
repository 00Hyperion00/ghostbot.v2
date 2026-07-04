4B.4.3.6.6.37L - Production Hardening Final Closure

Purpose
- Final audit for Phase 37 P0 production hardening.
- Seal no-submit production readiness after P0-1..P0-10 are closed.
- Declare remote tag audit contract without performing network/git mutation.

Safety
- No paper transition approval.
- No live-real approval.
- No exchange submit approval.
- No runtime start, reload, training, overlay activation, order submit, HTTP request, signed request or network request.
- No report delete/move/archive/dedup.
- No git add/commit/tag/push.

Apply
  python tools/apply_4B436637L_production_hardening_final_closure.py

Check
  set PYTHONPATH=src
  python tools/check_4B436637L_production_hardening_final_closure.py --once-json

Test
  set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  set PYTHONPATH=src
  python -m pytest -q tests/test_production_hardening_final_closure_4B436637L.py
  python -m compileall -q -x "(_patch_backup|_patch_payload|legacy_patches)" src tools tests

Run
  set PYTHONPATH=src
  python tools/run_4B436637L_production_hardening_final_closure.py --reports-dir .\reports\recovery --once-json
