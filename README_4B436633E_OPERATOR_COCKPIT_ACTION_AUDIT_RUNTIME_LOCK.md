# 4B.4.3.6.6.33E — Operator Cockpit Action Audit & Runtime Lock

Bu patch 33D üzerine çalışır ve Operator Cockpit'e action audit + runtime lock görünürlüğü ekler.

## Eklenenler

- Engine start/stop/restart action audit outcome sınıflandırması
- Operator action ledger summary
- Runtime lock diagnostic snapshot
- Duplicate cockpit instance block visibility
- Stale runtime lock diagnostic
- Typed-confirm stale lock clear endpoint
- Shutdown reason visibility
- RED risk badge altında Force BUY entry guard visibility

## Güvenlik sınırları

- Live-real enablement yapılmaz.
- Order path gevşetilmez.
- Auth policy gevşetilmez.
- Stale lock otomatik silinmez; `CONFIRM_CLEAR_STALE_RUNTIME_LOCK` typed confirmation gerekir.

## Test

```powershell
python tools/compile_operator_cockpit_4B436633E.py
pytest tests/test_operator_cockpit_4B436633E.py
python -m compileall -q src\tradebot\cockpit src\tradebot\cli.py
```
