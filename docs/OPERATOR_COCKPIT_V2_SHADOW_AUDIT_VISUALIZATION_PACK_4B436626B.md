# 4B.4.3.6.6.26B — Operator Cockpit V2 — Shadow Audit Visualization Pack

This overlay patch extends the 26A read-only operator cockpit with self-contained HYP-005-R1 quant visualization panels.

## Scope

- Keeps the 26A overview layout and read-only safety contract.
- Adds layered visualization tabs instead of crowding the main screen.
- Adds cumulative unique-sample timeline.
- Adds forward-return distribution buckets.
- Adds symbol-level sample density and mean-edge comparison.
- Adds symbol-level performance table.
- Adds timestamp-cluster net-edge visualization and detailed cluster table.
- Adds spread/slippage-proxy ranking.
- Adds MAE / MFE scatter visualization when ledger fields are available.
- Adds read-only scenario comparison for all R1 samples, worst-cluster exclusion, and slippage-proxy filtering.

## Safety contract

The visualization pack is intentionally read-only.

- No config mutation.
- No scheduler mutation.
- No model reload.
- No paper-mode enable.
- No live-mode enable.
- No order action.
- No POST request to Binance.
- Dashboard mutation methods remain blocked with `405 READ_ONLY_DASHBOARD_MUTATION_BLOCKED`.
- Charts are self-contained; no CDN or internet dependency is used.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436626B_operator_cockpit_v2_shadow_audit_visualization_pack_patch.zip" `
  -DestinationPath . `
  -Force
python tools/apply_4B436626B_operator_cockpit_v2_shadow_audit_visualization_pack.py
```

## Run

Stop the existing cockpit process with `Ctrl + C`, then start the 26B launcher:

```powershell
powershell -ExecutionPolicy Bypass -File tools\start_operator_cockpit_v2_4B436626B.ps1
```

Open:

```text
http://127.0.0.1:8090/dashboard
```

## Operator experience

The dashboard still presents summary cards first. Quant visualizations are placed in a tabbed analysis area so that advanced visibility does not turn the main screen into a crowded terminal.
