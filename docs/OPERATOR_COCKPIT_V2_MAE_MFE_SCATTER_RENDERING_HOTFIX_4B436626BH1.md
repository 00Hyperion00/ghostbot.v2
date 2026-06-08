# 4B.4.3.6.6.26B-H1 — Operator Cockpit V2 — MAE / MFE Scatter Rendering and Empty-State Accuracy Hotfix

This overlay hotfix repairs the read-only Operator Cockpit V2 MAE / MFE scatter panel without changing the HYP-005-R1 scheduler, ledger, risk engine, trading engine, or any execution permission.

## Root cause

The 26B scatter renderer scaled MAE values by a positive-only `maxX`. Real R1 MAE values are signed and commonly negative. Negative values were therefore rendered outside the visible SVG canvas even though the ledger contained valid MAE / MFE rows.

## Fix

- Preserves negative MAE values.
- Builds signed x-axis and y-axis domains with padding and zero inclusion.
- Scales points into the visible SVG canvas.
- Adds grid lines and signed axis placement.
- Adds tooltip fields: symbol, timestamp, MAE, MFE, and final edge.
- Shows `MAE / MFE verisi henüz oluşmadı.` only when no valid numeric pair exists.

## Safety contract

- No config mutation.
- No scheduler mutation.
- No model reload.
- No paper-mode enable.
- No live-mode enable.
- No order action.
- No Binance POST request.
- Dashboard mutation methods remain blocked with `405 READ_ONLY_DASHBOARD_MUTATION_BLOCKED`.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436626B_H1_operator_cockpit_v2_mae_mfe_scatter_rendering_empty_state_accuracy_hotfix_patch.zip" `
  -DestinationPath . `
  -Force
python tools/apply_4B436626B_H1_operator_cockpit_v2_mae_mfe_scatter_rendering_hotfix.py
```

Restart the existing 26B dashboard launcher after stopping the current cockpit process with `Ctrl + C`:

```powershell
powershell -ExecutionPolicy Bypass -File tools\start_operator_cockpit_v2_4B436626B.ps1
```
