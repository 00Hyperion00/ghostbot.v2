# 4B.4.3.6.6.33E — Status Conflict Resolver

## Amaç

33E, 33C/33D zincirinden sonra kalan evidence kalite problemlerini emir/runtime tarafına dokunmadan sınıflandırır:

- Filename/payload status conflict resolution
- Unknown evidence classifier
- Malformed JSON triage
- Deterministic evidence ledger üretimi

## Güvenlik kapsamı

Bu patch emir göndermez, exchange/network submit yapmaz, training veya model reload çalıştırmaz, runtime overlay açmaz, paper/live/live-real onayı vermez ve destructive cleanup yapmaz.

## Çıktılar

`tools/run_4B436633E_status_conflict_resolver.py --reports-dir reports/recovery --once-json` çalıştırıldığında şu raporlar üretilir:

- `4B436633E_status_conflict_resolver_*_ready|not_ready.json`
- `4B436633E_status_conflict_resolution_ledger_*.json`
- `4B436633E_unknown_evidence_classifier_ledger_*.json`
- `4B436633E_malformed_json_triage_ledger_*.json`

## Kabul kriteri

- 33D READY runtime safety lockdown raporu bulunmalı.
- Status conflict kayıtlarının tamamı deterministik precedence ile çözülmeli.
- Unknown evidence kayıtları non-decisive sınıflara ayrılmalı.
- Malformed JSON kayıtları triage ledger'a alınmalı.
