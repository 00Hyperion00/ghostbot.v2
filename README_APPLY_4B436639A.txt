4B.4.3.6.6.39A Paper Sandbox Runtime Start Approval Review

Apply:
  python tools/apply_4B436639A_paper_sandbox_runtime_start_approval_review.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436639A_paper_sandbox_runtime_start_approval_review.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_runtime_start_approval_review_4B436639A.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436639A_paper_sandbox_runtime_start_approval_review.py --reports-dir .\reports\recovery --once-json

Scope:
  Separate explicit operator approval review only. No runtime process start, no network order, no live, no exchange submit.
