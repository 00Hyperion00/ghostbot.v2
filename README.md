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
tradebot ai-service --model-path models/SOLUSDT_model.ubj --threshold 0.60
```

## Model eğitimi
```bash
tradebot train-model --symbol SOLUSDT --interval 1m --days 30 --out models/SOLUSDT_model.ubj
```

## Dashboard
`dashboard.py` ve `tradebot.ui.dashboard` aynı arayüzü başlatır. Dashboard artık kaynak kodu patchlemez; doğrudan CLI ve HTTP ile çalışır.

## Production Architecture

Aktif runtime, operator workflow ve güvenlik sınırları için canonical rehber: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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

<!-- 4B436633A_OPERATOR_COCKPIT -->
## TradeBot V2 Operator Cockpit

33A itibarıyla önerilen tek başlatma yolu:

```bash
tradebot cockpit --config config.local.yaml
```

Windows tek tık başlatma için `run_cockpit.bat` veya `run_cockpit.ps1` kullanılabilir. Eski `run_dashboard.bat`, `start_dashboard.bat`, `start_tradebot.bat` dosyaları legacy kabul edilir.

<!-- 4B436633B_OPERATOR_COCKPIT_RUNTIME_HARDENING -->
## 33B Operator Cockpit Runtime Hardening

33B ile cockpit'e base-balance awareness banner, orphan local position recovery warning, runtime risk badge ve favicon cleanup eklendi.

Windows compile kontrolü için glob kullanma. Doğru komut:

```powershell
python tools/compile_operator_cockpit_4B436633B.py
```

<!-- 4B436633C_OPERATOR_COCKPIT_SECURITY_GATE -->
## 33C Operator Cockpit Security Gate

33C ile cockpit API auth guard, read-only health exception, typed confirmation UI modal, operator identity header ve danger-zone audit visibility eklendi.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633C.py
pytest tests/test_operator_cockpit_4B436633C.py
```

<!-- 4B436633C_H1_OPERATOR_COCKPIT_AUTH_BOOTSTRAP_HOTFIX -->
## 33C-H1 Operator Cockpit Auth Bootstrap Hotfix

33C sonrası token/operator boşken oluşan protected API 503 ve WebSocket 403 retry gürültüsü UI tarafında fail-closed onboarding ile düzeltildi.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633C_H1.py
pytest tests/test_operator_cockpit_4B436633C_H1.py
```

<!-- 4B436633D_OPERATOR_COCKPIT_UX_HEALTH_OBSERVABILITY -->
## 33D Operator Cockpit UX & Health Observability

Operator Cockpit artık Auth Status Card, Connection State Machine, heartbeat age, CPU/RAM metrics, engine uptime ve protected action disable reason görünürlüğü sunar.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633D.py
pytest tests/test_operator_cockpit_4B436633D.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

<!-- 4B436633E_OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK -->
## 33E Operator Cockpit Action Audit & Runtime Lock

Operator Cockpit artık runtime lock diagnostic, stale lock typed-confirm clear, duplicate instance block visibility, action audit summary, shutdown reason visibility ve RED risk badge entry guard görünürlüğü sunar.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633E.py
pytest tests/test_operator_cockpit_4B436633E.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

<!-- 4B436633F_OPERATOR_COCKPIT_RISK_RECONCILIATION -->
## 33F Operator Cockpit Risk Reconciliation

Operator Cockpit artık base balance present / position not tracked durumunu reconciliation akışıyla gösterir, read-only balance review sunar, manual acknowledgement kaydeder ve mismatch çözülmeden entry actionlarını bloklu tutar.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633F.py
pytest tests/test_operator_cockpit_4B436633F.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

<!-- 4B436633G_OPERATOR_COCKPIT_RECONCILIATION_EXECUTION -->
## 33G Operator Cockpit Reconciliation Execution

Operator Cockpit artık read-only balance snapshot confirmation, tracked position adoption candidate, dust-safe base balance resolution, manual reconciliation decision ledger ve runtime snapshot check helper içerir. Entry guard yalnızca reconciliation clear durumunda release edilir.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633G.py
pytest tests/test_operator_cockpit_4B436633G.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

<!-- 4B436633H_OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY -->
## 33H Operator Cockpit Reconciliation Decision Apply Flow

Operator Cockpit artık tracked position candidate review, dust-safe clear validation, manual reconciliation decision persistence, entry guard release verification ve runtime lock owner mismatch resolver görünürlüğü içerir.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633H.py
pytest tests/test_operator_cockpit_4B436633H.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```

<!-- 4B436633I_OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE -->
## 33I Operator Cockpit Separate Engine Position Recovery Gate

Operator Cockpit artık reviewed candidate -> manual recovery plan, typed plan confirmation, recovery ledger ve recovery completion verification helper içerir. Engine position state otomatik mutate edilmez; entry guard live read-only verification mismatch kapanana kadar bloklu kalır.

Windows test komutu:

```powershell
python tools/compile_operator_cockpit_4B436633I.py
pytest tests/test_operator_cockpit_4B436633I.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```

## 4B.4.3.6.6.33I-H1 Operator Cockpit Engine Position Recovery Key Hotfix

- Fixes missing `_engine_position_recovery_key` runtime snapshot/WebSocket NameError.
- No live-real/order/auth/risk threshold relaxation.

<!-- 4B436633J_OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE -->
## 33J Operator Cockpit Recovery Plan Apply & Verification Gate

Operator Cockpit now includes a 33J recovery-plan apply gate: create plan from reviewed candidate, confirm manual external recovery, verify no-mismatch from read-only runtime snapshot, write recovery completion ledger, and keep entry guard blocked until verified no-mismatch.

Safety: no automatic position mutation, no live-real enablement, no order-path relaxation, no auth policy relaxation.

<!-- 4B436633J_H1_OPERATOR_COCKPIT_RECOVERY_PLAN_ACTION_ROUTE_HOTFIX -->
## 33J-H1 Operator Cockpit Recovery Plan Action Route Hotfix

Fixes recovery-plan apply endpoint 500s caused by stale `require_operator_identity(context)` route calls. The hotfix only updates action-route operator identity binding; no order path, live-real, auth policy, or position mutation behavior is changed.

<!-- 4B436633K_OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE -->
## 33K Operator Cockpit External Recovery Evidence Gate

Operator Cockpit now requires external/manual recovery evidence plus a fresh read-only no-mismatch snapshot before verify-no-mismatch safe apply can release the entry guard.

Safety: no automatic position mutation, no order path relaxation, no live-real enablement, no auth policy relaxation.

<!-- 4B436633L_OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE -->
## 33L Operator Cockpit Exchange Environment Consistency & Fresh Balance Source Gate

Operator Cockpit now rejects stale `engine_status_balances` as a no-mismatch verification source. Manual recovery release requires config environment audit, a fresh exchange balance read, and no-mismatch verification from the verified fresh source.

Safety: no automatic position mutation, no order path relaxation, no live-real enablement, no auth policy relaxation.

<!-- 4B436633M_OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION -->
## 33M Operator Cockpit Engine Status Balance Cache Reconciliation

Operator Cockpit now invalidates stale `engine_status_balances` for cockpit risk/entry decisions after 33K/33L safe apply has verified no active mismatch from a fresh exchange balance source. Risk badge and entry guard can be recomputed from the verified fresh source view without mutating engine position state.

Safety: no automatic position mutation, no order path relaxation, no live-real enablement, no auth policy relaxation.


## 4B.4.3.6.6.34 Demo Entry Execution Controlled Re-Enablement

Adds demo-only controlled entry execution dry-run, filter verification, order intent audit, demo-only authorization, and post-entry protective-exit verification.

<!-- 4B436637B_INSTALL_CONTRACT_START -->

## Install Contract — 4B.4.3.6.6.37B

Canonical dependency source is `pyproject.toml` `[project].dependencies`.
`requirements.txt` is a generated compatibility file for Windows launcher and quick-start flows.

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

No paper/live/live-real, runtime overlay, training, reload, or order-submit permission is granted by this install contract.

<!-- 4B436637B_INSTALL_CONTRACT_END -->
