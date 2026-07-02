# 4B.4.3.6.6.33I — Operator Cockpit Separate Engine Position Recovery Gate

Bu patch 33H üzerine çalışır.

## Eklenenler

- Reviewed Candidate To Recovery Plan
- Manual Recovery Plan Confirmation
- No Auto Position Mutation
- Recovery Ledger
- Entry Guard Remains Blocked Until Engine Position Verified
- Recovery Completion Verification Helper 33I

## Güvenlik sınırları

- Engine/runtime position state otomatik mutate edilmez.
- Recovery plan sadece ledger kaydıdır; dış/manual recovery tamamlanmadan Force BUY açılmaz.
- Verification sadece live read-only snapshot mismatch kapandıysa başarılı olur.
- Live-real enablement yapılmaz.
- Order path gevşetilmez.
- Auth policy gevşetilmez.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633I.py
pytest tests/test_operator_cockpit_4B436633I.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```

## Runtime kontrol

```powershell
python tools/check_cockpit_runtime_4B436633I.py --token uzun-rastgele-token --operator operator-local
```
