# 4B.4.3.6.6.33D — Operator Cockpit UX & Health Observability

Bu patch, 33C-H1 sonrası cockpit güvenlik bootstrap davranışını daha okunabilir hale getirir ve sistem sağlığını operatör ekranına taşır.

## Kapsam

- Auth Status Card
- Connection State Machine
- Heartbeat Age sınıflandırması
- CPU/RAM metric snapshot; `psutil` yoksa güvenli fallback
- Engine uptime ölçümü
- Protected action disable reasons paneli
- Disabled button tooltip/reason görünürlüğü

## Değişmeyenler

- Live-real açılmaz.
- Order submit path değişmez.
- Strategy/risk threshold değişmez.
- Auth policy gevşetilmez.
- Runtime/order mutasyonu yapılmaz.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633D.py
pytest tests/test_operator_cockpit_4B436633D.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```
