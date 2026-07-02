# 4B.4.3.6.6.32B-H1 — Operator Cockpit Unified Desktop Sync

Amaç: `TradeBot V2 Operator Cockpit`, `run_dashboard.bat`, `start_dashboard.bat`, `start_tradebot.bat` karmaşasını tek masaüstü uygulamasına indirmek.

## Uygula

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436632B_H1_operator_cockpit_unified_sync_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436632B_H1_operator_cockpit_unified_sync.py
```

## Kontrol + test

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436632B_H1_operator_cockpit_unified_sync.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_operator_cockpit_unified_4B436632B_H1.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches|_legacy_launchers)' `
  src tools tests
```

## Başlat

```powershell
.\start_tradebot_v2_operator_cockpit.bat
```

Alternatif isim:

```powershell
.\"TradeBot V2 Operator Cockpit.bat"
```

## Masaüstü kısayolu oluştur

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\install_desktop_operator_cockpit_shortcut_4B436632B_H1.ps1
```

## Snapshot üret

```powershell
$env:PYTHONPATH="src"
python tools/run_operator_cockpit_unified.py --snapshot-json --no-status-endpoint
python tools/run_operator_cockpit_unified.py --write-snapshot
```

## Commit

```powershell
git status --short
git add -A
git commit -m "4B.4.3.6.6.32B-H1 operator cockpit unified desktop sync"
git tag -a 4B.4.3.6.6.32B-H1 -m "Accepted operator cockpit unified desktop sync"
git push origin main
git push origin 4B.4.3.6.6.32B-H1
```

Risk kontratı: canlı emir yok, Binance submit yok, `32B` sadece submit-request evidence olarak kalır. Gerçek ikinci micro-canary submit için ayrı `32C` fazı gerekir.
