# 4B.4.3.6.6.33G — Operator Cockpit Reconciliation Execution

Bu patch 33F üzerine çalışır.

## Eklenenler

- Read-Only Balance Snapshot Confirmation
- Tracked Position Adoption Candidate
- Dust-Safe Base Balance Resolution
- Manual Reconciliation Decision Ledger
- Entry Guard Release Only After Reconciliation Clear
- Runtime Snapshot Check Helper

## Güvenlik sınırları

- Tracked position adoption candidate engine/runtime position state mutate etmez.
- Dust-safe resolution sadece tradable base <= dust threshold ise entry guard release yetkisi verir.
- Base balance/position mismatch sürüyorsa Force BUY bloklu kalır.
- Live-real enablement yapılmaz.
- Order path gevşetilmez.
- Auth policy gevşetilmez.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633G.py
pytest tests/test_operator_cockpit_4B436633G.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```

## Runtime kontrol

```powershell
python tools/check_cockpit_runtime_4B436633G.py --token uzun-rastgele-token --operator operator-local
```
