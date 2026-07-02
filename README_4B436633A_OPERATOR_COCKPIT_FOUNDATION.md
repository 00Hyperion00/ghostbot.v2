# 4B.4.3.6.6.33A — TradeBot V2 Operator Cockpit Foundation

Bu paket tek komutlu Operator Cockpit foundation patch'idir.

## Uygulama

Repo kök dizininde çalıştır:

```powershell
python apply_4B436633A_operator_cockpit_foundation.py
```

## Sonrasında test

```powershell
python -m py_compile src/tradebot/cockpit/*.py src/tradebot/cli.py
pytest tests/test_operator_cockpit_4B436633A.py
```

## Çalıştırma

```powershell
tradebot cockpit --config config.local.yaml
```

veya Windows başlatıcı:

```powershell
.\run_cockpit.ps1
```

## Eklenen ana parçalar

- `src/tradebot/cockpit/orchestrator.py`
- `src/tradebot/cockpit/app.py`
- `src/tradebot/cockpit/broadcaster.py`
- `src/tradebot/cockpit/static/*`
- `run_cockpit.bat`
- `run_cockpit.ps1`
- `docs/OPERATOR_COCKPIT_4B436633A.md`

## Not

Bu foundation patch canlı emir yolunu gevşetmez. Danger-zone aksiyonları typed confirmation ister.
