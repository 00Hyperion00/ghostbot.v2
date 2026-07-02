# 4B.4.3.6.6.33A — TradeBot V2 Operator Cockpit Foundation

Bu patch, eski `run_dashboard.bat`, `start_dashboard.bat`, `start_tradebot.bat` dağınıklığını azaltmak için tek bir web tabanlı Operator Cockpit foundation ekler.

## Yeni komut

```bash
tradebot cockpit --config config.local.yaml
```

Tarayıcı otomatik açılır. Otomatik açılmasını istemezsen:

```bash
tradebot cockpit --config config.local.yaml --no-open-browser
```

Engine cockpit açılır açılmaz başlasın istersen:

```bash
tradebot cockpit --config config.local.yaml --auto-start-engine
```

## Yeni bileşenler

- `src/tradebot/cockpit/orchestrator.py`
- `src/tradebot/cockpit/app.py`
- `src/tradebot/cockpit/broadcaster.py`
- `src/tradebot/cockpit/static/index.html`
- `src/tradebot/cockpit/static/app.js`
- `src/tradebot/cockpit/static/styles.css`
- `run_cockpit.bat`
- `run_cockpit.ps1`

## Güvenlik notu

Danger-zone aksiyonları typed confirmation ister:

- `CONFIRM_FORCE_BUY`
- `CONFIRM_FORCE_SELL`
- `CONFIRM_CANCEL_PENDING`
- `CONFIRM_RISK_RESET`
- `CONFIRM_SAFE_MODE_TOGGLE`

## Legacy BAT policy

Eski `.bat` dosyaları hemen silinmez. 33A itibarıyla canonical başlatıcı `tradebot cockpit` ve `run_cockpit.*` dosyalarıdır.
