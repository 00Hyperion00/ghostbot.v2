# 4B.4.3.6.6.33B — Operator Cockpit Runtime Hardening

Bu patch, 33A Operator Cockpit Foundation üzerine çalışır.

## Eklenenler

- PowerShell compile helper: `tools/compile_operator_cockpit_4B436633B.py`
- `/favicon.ico` route ve `favicon.svg`
- Base-balance awareness banner
- Orphan local position recovery warning
- Cockpit risk badge: GREEN / YELLOW / RED
- 33B test dosyası

## Uygulama

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633B_operator_cockpit_runtime_hardening_patch.zip" `
  -DestinationPath . `
  -Force
python apply_4B436633B_operator_cockpit_runtime_hardening.py
```

## Test

PowerShell glob kullanma. Doğru kontrol:

```powershell
python tools/compile_operator_cockpit_4B436633B.py
pytest tests/test_operator_cockpit_4B436633B.py
```

Opsiyonel tüm cockpit compile:

```powershell
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

## Güvenlik notu

Bu patch canlı emir yolunu açmaz, live-real/paper gate gevşetmez, strategy threshold değiştirmez. Sadece operator cockpit runtime görünürlüğünü artırır.
