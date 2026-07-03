# 4B.4.3.6.6.37K — Promotion Gate Isolation

No-Submit Production Hardening P0-10 patch.

Scope:
- shadow/paper/live/submit gate separation
- no cross-phase auto-promotion
- explicit approval required for promotion transitions
- all P0 closed does not unlock paper/live/submit
- no runtime promotion state mutation

Apply:
```powershell
python tools/apply_4B436637K_promotion_gate_isolation.py
```

Check:
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436637K_promotion_gate_isolation.py --once-json
python -m pytest -q tests/test_promotion_gate_isolation_4B436637K.py
```

Run reports:
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436637K_promotion_gate_isolation.py --reports-dir .eportsecovery --once-json
```
