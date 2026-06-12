# 4B.4.3.6.6.27G-H1 — Repository Hygiene Cleanup

This hotfix removes generated runtime artifacts and patch working directories from the Git index without deleting local files.

Ignored paths:

- `reports/hyp005_r1_canonical/`
- `tools/_patch_backup_*/`
- `tools/_patch_payload_*/`

The patch does not modify trading configuration, scheduler state, model files, runtime permissions, or order execution code.
