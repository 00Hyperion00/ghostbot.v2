4B.4.3.6.6.37C Repo Hygiene Evidence Retention

Purpose
- Close P0-2: P0_REPO_HYGIENE_EVIDENCE_RETENTION.
- Produce Canonical Reports Policy evidence.
- Produce Patch Backup Retention Guard evidence.
- Keep Phase 37 planning-only and no-submit.

Apply
```powershell
python tools/apply_4B436637C_repo_hygiene_evidence_retention.py
```

Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436637C_repo_hygiene_evidence_retention.py --once-json
```

Run
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436637C_repo_hygiene_evidence_retention.py --reports-dir .\reports\recovery --once-json
```

Safety
- No report delete.
- No report move.
- No deduplication.
- No patch backup delete/move/archive.
- No network, submit, paper/live enable, runtime overlay, training, reload.
