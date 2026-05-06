# 4B.4.3.6.6.24L Regime-Aware Edge Filter Recovery

Purpose: find whether the two-stage ACTION/SIDE candidate has positive edge in specific market regimes rather than globally.

Safety contract:

- observation-only
- market data access is GET-only (`method="GET"`)
- `post_requests_allowed: false`
- no config mutation
- no model reload
- no paper trading start
- no live-real permission
- no order actions

Recommended run using the 24I cost-aware policy report:

```powershell
python tools/run_regime_aware_edge_filter_recovery_4B436624L.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --input-json reports/4B436624I_cost_aware_label_policy_recovery_20260506_121817.json `
  --max-candidates 6 `
  --review-ok
```

Aggregate 24K reports can be inspected, but they do not include per-sample regime features. In that mode the tool intentionally blocks with `REGIME_SAMPLE_FEATURES_MISSING`.

A PASS means only: a regime filter may be used as a training-candidate filter in a later phase. It is not a paper/live approval.
