# 4B.4.3.6.6.61-H4 — Production Hardening Package Export / H2 Regression / Cockpit Telemetry Version Hotfix

## Scope

- `production_hardening_signature_compatibility_v2` korunur.
- `production_hardening_signature_compatibility_h3` korunur.
- `src/tradebot/production_hardening/__init__.py` varsa export kesinleştirilir; yoksa module fallback korunur.
- `OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION` ve failing cockpit parity testinin import ettiği `OPERATOR_COCKPIT_V2_*` sembolleri geri eklenir.
- H1/H2/H3 testleri birlikte korunur.

## Non-goals

No paper submit, no network order, no live-real approval, no exchange submit, no private API access, no runtime start, no reload, no training, no destructive cleanup.
