# 4B.4.3.6.6.29B API / Operator Security Hardening

This patch hardens local API operator actions without enabling paper/live/live-real order flow.

## Controls

- Destructive endpoint typed confirmation.
- Constant-time API token comparison.
- Token TTL guard when `api_auth_enabled=True` and TTL is configured.
- Live-real start arm TTL and separate live arm confirmation.
- Operator audit events for blocked and allowed destructive API calls.
- Local-only API client guard.

## Safety decision

- HYP-006 remains isolated.
- Runtime overlay activation remains blocked.
- Paper/live/live-real remains blocked.
- Training/reload is not performed by this patch.
- No order action is performed by this patch.
