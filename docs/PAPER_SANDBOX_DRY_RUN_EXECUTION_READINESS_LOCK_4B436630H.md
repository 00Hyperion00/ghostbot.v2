# 4B.4.3.6.6.30H Paper Sandbox Dry-run Execution Readiness Lock

This phase consumes the 30G execution-candidate gate and requires an explicit operator dry-run readiness lock.

Fail-closed guarantees:

- 30G ready candidate evidence is required.
- Operator explicit dry-run lock is TTL-bound and typed.
- Exchange submit remains hard-blocked.
- Paper sandbox dry-run execution remains disabled.
- Paper candidate remains blocked.
- Live-real remains blocked.
- No order, exchange submit, runtime overlay, training, reload, scheduler mutation, or strategy parameter mutation is performed.
