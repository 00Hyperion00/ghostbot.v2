# 4B.4.3.6.6.33C-H1 — Operator Cockpit Auth Bootstrap Hotfix

Bu hotfix, 33C güvenlik kapısı sonrası token/operator boşken oluşan 403/503 WebSocket retry gürültüsünü kapatır.

## Kapsam

- UI önce `/api/cockpit/health` üzerinden public auth policy okur.
- Server token tanımlı değilken protected API ve WebSocket çağrısı başlatılmaz.
- UI token alanı boşken WebSocket retry yapılmaz.
- WebSocket `1008` auth rejection sonrası otomatik retry durur.
- Operatöre PowerShell token bootstrap talimatı gösterilir.
- Protected butonlar auth bootstrap tamamlanana kadar disable edilir.

## Hızlı runtime çözüm

Elevated runtime kullanıyorsan cockpit başlatmadan önce token tanımla:

```powershell
$env:TRADEBOT_COCKPIT_AUTH_TOKEN="uzun-rastgele-token"
tradebot cockpit --config config.local.yaml
```

Tarayıcıda:

```text
Operator   : operator-local veya kendi operatör adın
Auth Token : aynı token
Save
```

## Değişmeyenler

- Live-real açılmaz.
- Order submit policy gevşetilmez.
- Strategy/risk threshold değiştirilmez.
- Engine/runtime/order path mutasyonu yapılmaz.
- Auth policy zayıflatılmaz; sadece UI bootstrap ve retry davranışı düzeltilir.
