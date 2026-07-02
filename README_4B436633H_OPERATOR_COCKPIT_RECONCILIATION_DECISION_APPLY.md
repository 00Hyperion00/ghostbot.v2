# 4B.4.3.6.6.33H — Operator Cockpit Reconciliation Decision Apply Flow

Bu patch 33G üzerine çalışır.

## Eklenenler

- Tracked Position Candidate Review apply flow
- Dust-Safe Clear Validation apply flow
- Manual Reconciliation Decision Persistence
- Entry Guard Release Verification
- Runtime Lock Owner Mismatch Resolver
- Runtime Snapshot Check Helper 33H

## Güvenlik sınırları

- Tracked position candidate review engine/runtime position state mutate etmez.
- Dust-safe clear sadece dust threshold geçerliyse entry guard release verir.
- Tradable base balance dust değilse Force BUY bloklu kalır.
- Runtime lock owner mismatch otomatik temizlenmez; safe-clear sadece stale/dead owner durumunda typed confirmation ile yapılır.
- Live-real enablement yapılmaz.
- Order path gevşetilmez.
- Auth policy gevşetilmez.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633H.py
pytest tests/test_operator_cockpit_4B436633H.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```

## Runtime kontrol

```powershell
python tools/check_cockpit_runtime_4B436633H.py --token uzun-rastgele-token --operator operator-local
```
