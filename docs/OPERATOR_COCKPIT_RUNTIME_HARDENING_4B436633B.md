# 4B.4.3.6.6.33B — Operator Cockpit Runtime Hardening

33B, 33A Operator Cockpit Foundation üzerine gelen runtime görünürlük hotfix'idir.

## Kapsam

- PowerShell glob kaynaklı compile komut hatasını kaldıran compile helper.
- `/favicon.ico` route + SVG favicon ile tarayıcı 404 gürültüsü temizliği.
- Base-balance awareness banner.
- Orphan local position recovery warning.
- Cockpit UI risk badge: GREEN / YELLOW / RED.

## Değişmeyenler

- Live-real açılmaz.
- Paper/live gate gevşetilmez.
- Exchange submit policy değişmez.
- Strategy threshold değişmez.
- Auto entry davranışı engine içinde değiştirilmez.

## Doğru Windows compile kontrolü

PowerShell `*.py` glob'unu `python -m py_compile` için güvenilir biçimde expand etmediği için şu komut kullanılmalıdır:

```powershell
python tools/compile_operator_cockpit_4B436633B.py
```

Alternatif:

```powershell
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

## Risk badge anlamı

```text
GREEN  : Base balance / runtime position mismatch yok.
YELLOW : Base asset var ama position takip edilmiyor veya orphan recovery sinyali görüldü.
RED    : Orphan local position recovery sonrası tradable base balance position'sız duruyor veya aktif anomaly var.
```

## Operatör aksiyonu

YELLOW/RED görünürse yeni entry onayı vermeden önce:

1. Balance sync yap.
2. Recovery loglarını incele.
3. Cüzdandaki base asset'in bilinçli inventory mi yoksa artık exposure mı olduğunu doğrula.
4. Gerekirse manuel force-sell / reconcile kararı ver; typed confirmation olmadan danger-zone aksiyonları çalışmaz.
