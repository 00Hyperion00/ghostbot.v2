# 4B.4.3.6.6.30D-H1 Operator Approval Evidence Capture Settings Clone Hotfix

The 30D module attempted to pass `paper_live_order_enablement_present` into `Settings(...)` while cloning settings for approval capture. That key is a report flag, not a configuration field.

This hotfix removes that unsupported constructor key and verifies:

- default evidence capture remains input-required,
- explicit typed approval evidence capture becomes ready for 30C review only,
- paper transition candidate remains blocked,
- paper candidate remains blocked,
- live-real remains blocked,
- no order, runtime overlay, training, reload, scheduler mutation, or strategy parameter mutation is performed.
