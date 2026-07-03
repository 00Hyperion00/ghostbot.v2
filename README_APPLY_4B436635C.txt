# 4B.4.3.6.6.35C Runtime Evidence Collection Plan

This patch creates a planning-only runtime evidence collection plan after 35B.

Scope:
- Evidence Source Registry
- Collection Runbook Matrix
- No-Submit Collection Boundary

It does not perform runtime evidence collection, public market-data observation, private API reads, paper transition, live transition, runtime overlay, exchange/network/order submit, training, reload, delete, move, archive execution, or deduplication.

Apply:

```powershell
python tools/apply_4B436635C_runtime_evidence_collection_plan.py
```

Check:

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436635C_runtime_evidence_collection_plan.py --once-json
```

Run:

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436635C_runtime_evidence_collection_plan.py --reports-dir .eportsecovery --once-json
```
