# 4B.4.3.6.6.61-H6 Production Hardening Import Finalization / Cockpit Evidence Pack Callable Fix

Purpose:
- Fix `_build_risk_sizing_in_memory_evidence_pack` being a string instead of a callable.
- Preserve H4/H5 predicate reports by making all present callable/string contracts ready.
- Finalize `tradebot.production_hardening` import/export path through a self-contained compatibility module, package `__init__.py`, module bridge, and pytest collection finalizer.
- Preserve no paper submit / no network order / no live / no exchange-submit safety locks.

Apply:
```powershell
python tools/apply_4B436661_H6_production_hardening_import_finalization_cockpit_callable_fix.py
```

Check:
```powershell
python tools/check_4B436661_H6_production_hardening_import_finalization_cockpit_callable_fix.py --once-json
```

Run:
```powershell
python tools/run_4B436661_H6_production_hardening_import_finalization_cockpit_callable_fix.py --reports-dir .\reports\recovery --once-json
```
