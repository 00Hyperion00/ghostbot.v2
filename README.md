# TradeBot Python

Bu sürüm, Chrome eklentisinden ayrılmış Python çekirdeğidir.

## Dahil edilen ana bileşenler
- Spot trade motoru (`tradebot.engine`)
- Binance REST/WebSocket adapter (`tradebot.exchange.binance`)
- Teknik strateji + AI sinyal normalize katmanı (`tradebot.strategy`)
- XGBoost tabanlı AI model provider (`tradebot.ai.provider`)
- FastAPI AI servisi (`tradebot.ai.service`)
- XGBoost eğitim CLI'si (`tradebot.training.train_xgb`)
- Masaüstü dashboard (`tradebot.ui.dashboard`)
- SQLite persistence (`tradebot.persistence`)

## Hızlı başlangıç
```bash
pip install -r requirements.txt
tradebot api --config examples/config.demo.yaml
```

## AI servisini ayrı çalıştırma
```bash
tradebot ai-service --model-path models/SOLUSDT_model.json --threshold 0.60
```

## Model eğitimi
```bash
tradebot train-model --symbol SOLUSDT --interval 1m --days 30 --out models/SOLUSDT_model.json
```

## Dashboard
`dashboard.py` ve `tradebot.ui.dashboard` aynı arayüzü başlatır. Dashboard artık kaynak kodu patchlemez; doğrudan CLI ve HTTP ile çalışır.

## Notlar
- `main.py`, `train_model.py`, `dashboard.py` dosyaları korunmuştur ama artık yeni modüller için ince wrapper görevi görür.
- Model dosyaları `models/` altında tutulur.
- AI karar akışı artık ortak feature üretimi kullanır; eğitim ve inference aynı veri kolonlarıyla çalışır.


## Desktop Dashboard

Botu terminal yerine masaüstü panel ile açmak için:

```bash
tradebot dashboard --config config.local.yaml
```

Panel içinden:
- backend süreç başlat / durdur / yeniden başlat
- start / stop / force buy / force sell
- pending iptal / bakiye senkron / risk reset / safe mode
- config kaydet
- model seç / model eğit
- canlı durum ve log takibi

Yalnız dashboard çalışması için `customtkinter` kurulu olmalıdır.


### Windows Tek Tık Başlatma

- `run_dashboard.bat`
- `run_dashboard.ps1`

Bu scriptler sanal ortamı hazırlayıp dashboard'ı açar.
