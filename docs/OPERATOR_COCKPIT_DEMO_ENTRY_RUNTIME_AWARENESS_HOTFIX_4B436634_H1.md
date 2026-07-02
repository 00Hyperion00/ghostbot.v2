
# 4B.4.3.6.6.34-H1 — Demo Entry Runtime Awareness Snapshot Hotfix

Bu hotfix 34 patch sonrası görülen runtime 500 hatasını düzeltir.

## Kök neden

`build_exchange_environment_config_audit()` artık 33L kontratı gereği `runtime_awareness` keyword argümanı zorunlu istiyor. 34 içindeki `build_demo_entry_execution_gate_snapshot()` eski çağrı ile `build_exchange_environment_config_audit(settings)` çalıştırdığı için `/api/cockpit/snapshot`, WebSocket snapshot ve demo-entry endpointleri 500 hatasına düşüyordu.

## Düzeltmeler

- Demo-entry snapshot için read-only runtime-awareness helper eklendi.
- `build_exchange_environment_config_audit(settings, runtime_awareness=...)` çağrısı zorunlu hale getirildi.
- `force_buy()` eski 33F `_entry_guard_snapshot()` yolunu değil, tam 33M uyumlu snapshot entry guard’ını kullanacak şekilde düzeltildi.
- Live-real enablement, auth relaxation, order path mutation veya engine position mutation eklenmedi.

## Test

```powershell
python tools/compile_operator_cockpit_4B436634_H1.py
pytest tests/test_operator_cockpit_4B436634_H1.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```
