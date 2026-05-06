# 4B.4.3.6.6.24A Pre-live Hygiene Runbook

Amaç: live-demo/paper fazına geçmeden önce API degraded startup davranışını, secret hygiene politikasını ve temiz release paketlemeyi zorunlu hale getirmek.

## Kabul Kriterleri

1. `/health` bootstrap fail durumunda `ok=false`, `degraded=true`, `start_error` ve `bootstrap_error` döner.
2. `/status` bootstrap fail durumunda engine metodlarına yaslanmadan güvenli `STOPPED` fallback döner.
3. `Settings.to_dict()` varsayılan olarak `api_key` ve `api_secret` değerlerini maskeleyerek döner.
4. `config.local.yaml` gerçek credential içermez.
5. Temiz release arşivi `.venv`, cache, runtime DB, log, local config ve backup dosyalarını dışlar.

## Uygulama Sonrası Test

```powershell
python tools/apply_4B436624A_pre_live_hygiene.py
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_api_persistence_hotfix.py tests/test_release_cleanup_4B436624A.py tests/test_config_loading.py tests/test_config_profile_safety.py
python tools/build_release_archive_4B436624A.py --root . --out-dir dist
```

## Operasyon Notu

`config.local.yaml` artık boş credential ile gelir. Çalıştırmadan önce Binance demo key/secret değerlerini kendi lokal makinenizde tekrar girin. Bu dosya `.gitignore` ve `.releaseignore` kapsamındadır; temiz release paketine alınmamalıdır.

Gerçek key daha önce zip içinde taşındıysa key iptal/rotate edilmelidir. Demo key bile olsa bu kural gevşetilmez.
