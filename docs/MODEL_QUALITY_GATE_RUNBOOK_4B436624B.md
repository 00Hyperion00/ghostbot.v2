# 4B.4.3.6.6.24B Model Quality Recovery / Retrain Gate Runbook

## Amaç

Bu patch, eğitilen XGBoost aday modelinin otomatik olarak aktif modele yüklenmesini kalite kapısına bağlar. Runtime tarafında da mevcut model kalite snapshot'ı canlı/demo arming için ayrı bir gate snapshot üretir.

## Bloklayan durumlar

- Runtime model quality `critical`, `disabled`, `no_data` veya `warming_up` ise live/demo arming BLOCK kabul edilir.
- `RETRAIN_RECOMMENDED` varsa live/demo arming BLOCK kabul edilir.
- Runtime HOLD oranı çok yüksekse veya actionable coverage çok düşükse BLOCK kabul edilir.
- Eğitim sonucu `clean_samples`, `calibrated_accuracy`, `action_coverage`, `hold_rate` kanıtlarını üretmiyorsa aday model reload edilmez.
- Eğitilen aday model HOLD-dominant ise veya calibrated accuracy/action coverage minimum kapıyı geçmiyorsa reload edilmez.

## Eğitim sonrası beklenen API davranışı

`POST /ai/train` artık response içinde `quality_gate` döner.

- `quality_gate.decision == PASS`: reload yapılabilir.
- `quality_gate.decision == WARN`: response uyarı taşır; manuel değerlendirme gerekir.
- `quality_gate.decision == BLOCK`: `reload_blocked=true`, `reloaded=false`, aktif model korunur.

## Rapor üretme

Runtime status JSON için:

```powershell
python tools/generate_model_quality_gate_4B436624B.py --mode runtime --input status.json --out-dir reports
```

Training result JSON için:

```powershell
python tools/generate_model_quality_gate_4B436624B.py --mode training --input training_result.json --out-dir reports
```

## Canlıya geçiş kararı

Bu gate tek başına canlı işlem izni değildir. Canlıya geçiş için ayrıca config safety, risk snapshot, reconciliation, soak ve acceptance metrikleri PASS olmalıdır.
