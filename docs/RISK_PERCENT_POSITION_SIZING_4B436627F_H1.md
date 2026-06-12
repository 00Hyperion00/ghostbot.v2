# 4B.4.3.6.6.27F-H1 Hotfix

Scope:

- Preserve stable external entry-block `skipCode` values while retaining the internal sizing diagnostic in `sizingReasonCode`.
- Deny new-risk BUY submission when the exchange adapter does not expose the mandatory entry-preflight method.
- Deny new-risk BUY submission when the entry-preflight adapter raises an unexpected exception.
- Update legacy test doubles so successful entry-lifecycle fixtures implement the truthful preflight contract.
- Keep configuration, scheduler, training, reload and trading actions untouched during patch application.

The patch does not enable paper or live order execution.
