# 4B.4.3.6.6.33I — Operator Cockpit Separate Engine Position Recovery Gate

Bu patch 33H üzerine çalışır.

## İçerik

- Reviewed Candidate To Recovery Plan
- Manual Recovery Plan Confirmation
- No Auto Position Mutation
- Recovery Ledger
- Entry Guard Remains Blocked Until Engine Position Verified
- Recovery Completion Verification Helper

## Güvenlik sınırları

- Engine/runtime position state otomatik mutate edilmez.
- Recovery plan ledger kaydıdır; manuel/dış recovery doğrulanmadan entry guard açılmaz.
- Verification sadece live read-only snapshot mismatch kapandıysa başarılı olur.
- Live-real enablement yoktur.
- Order path gevşetilmez.
- Auth policy gevşetilmez.

## Kurulum

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633I_operator_cockpit_separate_engine_position_recovery_gate_patch.zip" `
  -DestinationPath . `
  -Force
python apply_4B436633I_operator_cockpit_separate_engine_position_recovery_gate.py
```

## Test

```powershell
python tools/compile_operator_cockpit_4B436633I.py
pytest tests/test_operator_cockpit_4B436633I.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```

## Runtime kontrol

```powershell
python tools/check_cockpit_runtime_4B436633I.py --token uzun-rastgele-token --operator operator-local
```
