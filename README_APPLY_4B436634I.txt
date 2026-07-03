4B.4.3.6.6.34I — Post-Closure Tag Audit

Purpose:
- Verify 34H tag after 34H commit/push.
- Confirm clean worktree with 34I self-artifacts normalized as advisory-only until 34I commit.
- Produce No-Submit Phase-34 Final Seal evidence.

This patch does not:
- Enable exchange/network/order submit.
- Enable paper/live/live-real.
- Enable runtime overlay.
- Perform approval, file deletion, report deletion, archive execution, training, reload, or next-phase unlock.

Commands:

  python tools/apply_4B436634I_post_closure_tag_audit.py

  $env:PYTHONPATH="src"
  python tools/check_4B436634I_post_closure_tag_audit.py --once-json

  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_post_closure_tag_audit_4B436634I.py

  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

  $env:PYTHONPATH="src"
  python tools/run_4B436634I_post_closure_tag_audit.py --reports-dir .\reports\recovery --once-json
