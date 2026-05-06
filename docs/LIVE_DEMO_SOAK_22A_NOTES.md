# 4B.4.3.6.6.22a Soak Runner Notes

## What changed

- `/status.contract_version` is treated as the runtime engine/status contract, not the release tooling contract.
- Runtime contract `4B.4.3.6.6.12` or newer is accepted during the 4B.4.3.6.6.22 soak phase.
- Ctrl+C now writes a partial REVIEW report instead of producing a traceback.

## Operator interpretation

- `PASS`: no fail or warning reasons were observed.
- `REVIEW`: non-critical warning or operator-interrupted partial soak.
- `FAIL`: hard safety guard triggered.

The tool remains observation-only and GET-only.
