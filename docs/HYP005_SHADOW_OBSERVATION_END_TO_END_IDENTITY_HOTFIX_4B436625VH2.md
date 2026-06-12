# 4B.4.3.6.6.25V-H2 — HYP-005 End-to-End Canonical Identity Hotfix

This overlay aligns HYP-005 no-order shadow observation identity across the logger report, JSON ledger, JSONL ledger and the 25X merge boundary.

## Guarantees

- Canonical identity uses `hypothesis_id + symbol + timeframe + timestamp_utc`.
- Rolling-window ordinal remains only as `legacy_observation_id` when present.
- JSON, JSONL and report observations are validated for equivalence.
- 25X normalizes legacy rows at ingestion and deduplicates by canonical event key.
- JSONL is the single scheduler ingestion truth when both JSON and JSONL exist.
- Scheduler configuration is not mutated.
- No training, paper mode, live mode or order action is enabled.

## Post-install runtime audit

```powershell
python tools/check_hyp005_shadow_observation_identity_chain_4B436625VH2.py `
  --reports-dir reports\hyp005_r1_canonical `
  --require-runtime-chain `
  --once-json
```
