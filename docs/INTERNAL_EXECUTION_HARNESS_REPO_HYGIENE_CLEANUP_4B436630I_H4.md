# 4B.4.3.6.6.30I-H4 Internal Execution Harness Repo Hygiene Cleanup

Purpose:
- Remove tracked `_patch_backup` artifacts introduced during the 30I-H3 acceptance chain.
- Preserve the accepted 30I-H3 deterministic acceptance baseline.
- Make no runtime behavior change.

Risk posture:
- No exchange submit.
- No order action.
- No real paper execution enablement.
- No paper candidate approval.
- No live-real approval.
- No runtime overlay, training, reload, scheduler mutation, or strategy mutation.

Acceptance:
- `tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py --once-json` returns `ok=true`.
- `git ls-files -- _patch_backup tools/_patch_backup tests/_patch_backup docs/_patch_backup` returns no tracked files.
- 30I-H3 checker remains `ok=true`.
