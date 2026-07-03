# 4B.4.3.6.6.35G — Dry-Run Collector Closure

Bu patch 35F READY public data collection dry-run raporunu source gate olarak doğrular ve collection dry-run closure governance raporlarını üretir.

## Uygulama

```powershell
python tools/apply_4B436635G_dry_run_collector_closure.py
```

## Kontrol

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436635G_dry_run_collector_closure.py --once-json
python -m pytest -q tests/test_dry_run_collector_closure_4B436635G.py
python tools/run_4B436635G_dry_run_collector_closure.py --reports-dir .eportsecovery --once-json
```

## Güvenlik

- Collection çalıştırmaz.
- Public market data çağrısı yapmaz.
- Runtime probe çalıştırmaz.
- Private API/account read yapmaz.
- Paper/live/submit unlock yapmaz.
