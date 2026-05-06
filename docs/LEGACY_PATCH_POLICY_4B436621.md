# 4B.4.3.6.6.21c Legacy Patch Policy

## Stable baseline

The stable release-candidate baseline is:

```text
4B.4.3.6.6.20t11 + 4B.4.3.6.6.21a/21b
```

## Rule

Do not re-run historical `tools/apply_4B436620*.py` scripts after this baseline.
Those scripts were emergency repair patches from the dashboard contract recovery chain and can overwrite or reintroduce obsolete compatibility blocks.

## Recommended process

1. Run the scanner:

```powershell
python tools/check_patch_artifact_risk_4B436621.py
```

2. Review the generated reports under `reports/`.
3. Take a fresh project backup.
4. Dry-run the archive plan:

```powershell
python tools/archive_legacy_patch_scripts_4B436621.py
```

5. Only after review, move legacy patch scripts into quarantine:

```powershell
python tools/archive_legacy_patch_scripts_4B436621.py --apply
```

## Important

The archive tool never deletes files. It moves high-risk 4B436620 apply scripts into:

```text
tools/legacy_patches_4B436620/
```

Keep current 4B436621 release gate tooling in place.
