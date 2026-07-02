# 4B.4.3.6.6.33C — Operator Cockpit Security Gate

Patch paketi 33B üzerine uygulanmalıdır.

## Kurulum

```powershell
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads	rade_botV2_4B436633C_operator_cockpit_security_gate_patch.zip" `
  -DestinationPath . `
  -Force

python apply_4B436633C_operator_cockpit_security_gate.py
```

## Test

```powershell
python tools/compile_operator_cockpit_4B436633C.py
pytest tests/test_operator_cockpit_4B436633C.py
```

## Çalıştırma

```powershell
tradebot cockpit --config config.local.yaml
```

Token kullanan modlarda cockpit ekranındaki Auth Token ve Operator alanlarını doldurup Save'e basın.
