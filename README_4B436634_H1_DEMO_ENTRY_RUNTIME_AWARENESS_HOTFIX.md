# 4B.4.3.6.6.34-H1 — Demo Entry Runtime Awareness Snapshot Hotfix

34 sonrası görülen `/api/cockpit/snapshot` 500 hatasını düzeltir.

Kök hata:

```text
TypeError: build_exchange_environment_config_audit() missing 1 required keyword-only argument: 'runtime_awareness'
```

Patch sadece runtime-awareness çağrı uyumluluğunu ve force-buy entry guard yolunu düzeltir. Live-real enablement veya otomatik pozisyon mutation eklemez.
