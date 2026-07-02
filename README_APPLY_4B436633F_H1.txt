# Apply 4B.4.3.6.6.33F-H1 — Source 33E Completion Gate Hotfix

PowerShell:

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633F_H1_source_33e_gate_hotfix_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436633F_H1_source_33e_gate_hotfix.py
```
