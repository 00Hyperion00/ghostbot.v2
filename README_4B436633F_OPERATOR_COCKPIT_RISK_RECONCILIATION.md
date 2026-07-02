# 4B.4.3.6.6.33F — Operator Cockpit Risk Reconciliation

Bu patch 33E üzerine çalışır.

## Eklenenler

- Base Balance Present / Position Not Tracked Resolution Flow
- Reconcile Wizard
- Read-Only Balance Review
- Manual Position Acknowledgement Gate
- Entry Block Until Reconciled
- Always-On Entry Guard Snapshot

## Güvenlik sınırları

- Manual acknowledgement yeni entry izni vermez.
- RED risk badge / base-position mismatch çözülmeden Force BUY bloklu kalır.
- Live-real enablement yapılmaz.
- Order path gevşetilmez.
- Auth policy gevşetilmez.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633F.py
pytest tests/test_operator_cockpit_4B436633F.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```
