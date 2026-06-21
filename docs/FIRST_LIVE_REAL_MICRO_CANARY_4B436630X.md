# 4B.4.3.6.6.30X First Live-Real Micro Canary

Consumes the accepted 30W final operator approval and builds a single minimum-size live-real micro-canary submit request.

Risk invariants:

- Requires explicit 30X operator approval token.
- Single-order hard cap only.
- Leverage cap is 1x.
- Kill-switch must be armed.
- Automated network submit is disabled in this patch.
- Evidence may approve manual runtime handoff for one micro-canary request.
- The patch itself does not place a Binance order.
