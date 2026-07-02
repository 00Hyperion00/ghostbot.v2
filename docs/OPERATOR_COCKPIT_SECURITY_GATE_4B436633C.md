# 4B.4.3.6.6.33C — Operator Cockpit Security Gate

33C, 33A/33B Operator Cockpit üzerine gelen güvenlik kapısı hotfix'idir.

## Kapsam

- Cockpit API auth default guard.
- Read-only health exception: `/health` ve `/api/cockpit/health` açık kalır.
- Static shell public kalır; API ve WebSocket token gerektiren çalışma modlarında korunur.
- Typed confirmation UI modal.
- `X-TradeBot-Operator` operatör kimliği header'ı.
- Danger-zone aksiyon audit görünürlüğü.
- `operator_actions` ledger snapshot'ı cockpit ekranına taşınır.

## Auth politikası

Auth şu durumlarda zorunlu olur:

- `api_auth_enabled: true`
- `api_auth_token` veya `TRADEBOT_API_AUTH_TOKEN` / `TRADEBOT_COCKPIT_AUTH_TOKEN` tanımlıysa
- runtime elevated ise: `live_demo`, `live_real`, `spot_testnet`, `spot_mainnet`, `auto_trade_on_signal`, `live_trading_armed`, `live_real_double_confirm`

Auth zorunlu ama token yoksa cockpit API fail-closed davranır. Health endpointleri bu durumdan hariçtir.

## Header kontratı

```text
X-TradeBot-Auth      : cockpit API token
X-TradeBot-Operator  : operatör kimliği
X-TradeBot-Confirm   : typed confirmation metni
```

## Danger-zone typed confirmation

```text
trade.force_buy          -> CONFIRM_FORCE_BUY
trade.force_sell         -> CONFIRM_FORCE_SELL
trade.cancel_pending     -> CONFIRM_CANCEL_PENDING
risk.reset               -> CONFIRM_RISK_RESET
risk.safe_mode.toggle    -> CONFIRM_SAFE_MODE_TOGGLE
```

## Değişmeyenler

- Live-real açılmaz.
- Order submit policy gevşetilmez.
- Strategy/risk threshold değiştirilmez.
- Engine order path mutasyonu yapılmaz.
