# 4B.4.3.6.6.26D-H2-H2 — Operator Cockpit V2 — Evidence-Pack Response Preflight / Deterministic Native Export Timeout Contract Hotfix

## Scope

This overlay separates deterministic response-size validation from real evidence-pack generation time and converts native-export timeout failures into an explicit desktop-wrapper contract.

## Production repair

- Adds a named response preflight stage for `Content-Length` validation before response buffering.
- Rejects invalid, negative or oversized declared response lengths.
- Converts direct and `urllib`-wrapped socket timeout failures into:

```text
NATIVE_DESKTOP_EXPORT_TIMEOUT
```

- Gives evidence-pack downloads a dedicated 30-second timeout budget while keeping the default native-export timeout unchanged for smaller exports.
- Keeps local-loopback, allowlist-only and bounded-buffer rules intact.

## Deterministic test repair

The size-limit test no longer depends on the time needed to build a real evidence pack. It validates the preflight contract with a fixed `Content-Length` fixture. Separate tests cover:

- static oversized response preflight,
- malformed `Content-Length`,
- intentionally delayed response-header timeout,
- small ZIP payload success,
- extended evidence-pack bridge timeout selection.

## Security

- No external origin access.
- No redirect following.
- No config mutation.
- No scheduler mutation.
- No trading action.
- No paper or live enablement.
