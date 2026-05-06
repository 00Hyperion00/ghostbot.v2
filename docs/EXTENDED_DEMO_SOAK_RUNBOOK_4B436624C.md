# 4B.4.3.6.6.24C Extended Demo Soak + Model Gate Reporting

Amaç: 24A/24B sonrası demo/paper fazına geçmeden önce runtime stabilitesini, model gate kararlarını ve pre-paper readiness durumunu aynı kanıt setinde toplamak.

Bu araç observation-only çalışır. Sadece `/health` ve `/status` için GET çağrısı yapar. Emir göndermez, ayar değiştirmez, model reload etmez, training başlatmaz ve gerçek canlı işlem arming yapmaz.

## Hızlı doğrulama

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_extended_demo_soak_4B436624C.py
```

Beklenen: `6 passed`

## Tek örnek smoke

```powershell
python tools/run_extended_demo_soak_4B436624C.py --once --review-ok
```

## Kısa kontrollü soak

```powershell
python tools/run_extended_demo_soak_4B436624C.py --duration-min 30 --interval-sec 60 --min-samples 20 --review-ok
```

## Uzun extended demo soak

```powershell
python tools/run_extended_demo_soak_4B436624C.py --duration-min 240 --interval-sec 60 --min-samples 180
```

## Üretilen raporlar

- `reports/4B436624C_extended_demo_soak_*.json/.md`
- `reports/4B436624C_model_gate_timeline_*.json/.md`
- `reports/4B436624C_pre_paper_readiness_*.json/.md`

## PASS kriteri

- Health/API running olmalı.
- Runtime degraded olmamalı.
- Gerçek canlı işlem armed olmamalı.
- Config kritik uyarı üretmemeli.
- Websocket connected olmalı.
- Account/position/pending consistency anomalisi olmamalı.
- `model_quality_gate_snapshot.decision` tüm örneklerde `PASS` olmalı.
- `model_quality_gate_snapshot.live_demo_allowed` tüm örneklerde `true` olmalı.

## Risk yöneticisi notu

24C `PASS` bile gerçek canlı işlem izni değildir. Sadece Faz 5 Paper Trading başlangıcı için kanıt seviyesini yükseltir. Gerçek canlı işlem için ayrıca sınırlı canlı işlem gate'i, kill-switch, daily-loss ve position-risk kontrolleri PASS üretmelidir.
