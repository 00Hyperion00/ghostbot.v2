# 4B.4.3.6.6.22 Live-demo Supervised Soak Test Runbook

## Amaç

Bu faz kod geliştirme fazı değildir. Amaç release-candidate build'i canlı-demo ortamda gözlemlemek, risk/config/model/performance snapshot'larını toplamak ve operatör gözetiminde soak raporu üretmektir.

## Kesin kurallar

- Bu fazda gerçek canlı trade arming yok.
- `live_trading_armed=false` kalmalı.
- `live_real_double_confirm=false` kalmalı.
- Eski `4B436620` dashboard patch scriptleri tekrar çalıştırılmamalı.
- Soak tool observation-only çalışır; yalnızca GET `/health` ve `/status` kullanır.

## API başlatma

PowerShell 1 açık kalacak:

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
$env:PYTHONPATH="$PWD\src"
python -m tradebot.cli api --config config.local.yaml --host 127.0.0.1 --port 8000
```

## Hızlı smoke soak

PowerShell 2:

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
python tools/run_live_demo_soak_4B436622.py --base-url http://127.0.0.1:8000 --once
```

## Denetimli kısa soak

```powershell
python tools/run_live_demo_soak_4B436622.py --base-url http://127.0.0.1:8000 --duration-min 15 --interval-sec 30 --min-samples 10 --review-ok
```

## Uzun soak

```powershell
python tools/run_live_demo_soak_4B436622.py --base-url http://127.0.0.1:8000 --duration-min 60 --interval-sec 60 --min-samples 30 --review-ok
```

## PASS kriterleri

- `/health.ok == true`
- `/health.running == true`
- `/health.bootstrap_ok == true`
- `/status` okunabilir
- execution mode `live_demo`, `paper` veya `dry_run`
- market type `spot_demo`, `paper` veya `dry_run`
- real live armed değil
- double confirm real live açık değil
- critical config warning yok
- account health anomaly yok
- model quality critical değil

## REVIEW kriterleri

- Pozisyon veya pending demo state varsa tool REVIEW verebilir.
- WS kısa süre disconnected ise REVIEW üretilebilir.
- REVIEW operatör onayıyla kabul edilir; ancak sebep raporda açıkça yazmalıdır.

## FAIL kriterleri

- API kapalı
- `/health` veya `/status` okunamıyor
- bootstrap fail
- gerçek canlı arming açık
- config critical warning var
- account/pending/position health anomaly var
- model quality critical

## Çıktılar

```text
reports/4B436622_live_demo_soak_<timestamp>.json
reports/4B436622_live_demo_soak_<timestamp>.md
```
