# 4B.4.3.6.6.25AB — HYP-005 Shadow Observation Quality / Slippage Risk Audit

This patch adds a no-order quality and slippage audit gate for HYP-005 shadow observations.

## Purpose

The 25AA controlled symbol expansion increased the HYP-005 shadow universe to 10 symbols. Once the collection reached early-sample territory, 25AB inspects whether the collected observations are usable for continued no-order monitoring.

25AB checks:

- Symbol distribution and dominant-symbol dependency.
- Maturity-pending observations where `forward_return_bps_final` is not ready yet.
- True required-field missingness, excluding maturity-pending final returns.
- Per-symbol forward edge, win rate, profit factor, MAE/MFE, and slippage proxy.
- High-slippage symbols such as DOGEUSDT or AVAXUSDT when they exceed limits.

## Safety

25AB is an audit-only gate.

It does not:

- Train models.
- Reload models.
- Start paper trading.
- Enable live trading.
- Send POST requests.
- Send orders.
- Mutate trading configuration.

## Run

```powershell
$env:PYTHONPATH="src"
python tools/run_hyp005_shadow_quality_audit_4B436625AB.py `
  --reports-dir reports `
  --out-dir reports `
  --include-all `
  --review-ok
```

## Expected Output

The tool writes:

- `reports/4B436625AB_hyp005_shadow_quality_slippage_audit_*.json`
- `reports/4B436625AB_hyp005_shadow_quality_slippage_audit_*.md`

The decision may be one of:

- `HYP005_SHADOW_QUALITY_AUDIT_CONTINUE_COLLECTION`
- `HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED`
- `HYP005_SHADOW_QUALITY_AUDIT_BLOCK`

Paper/live remain blocked regardless of the decision.
