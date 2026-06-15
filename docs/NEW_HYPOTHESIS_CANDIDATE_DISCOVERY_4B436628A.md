# 4B.4.3.6.6.28A — New Hypothesis Candidate Discovery

This patch adds a read-only research selection pack after the HYP-005-R1 no-promotion closure evidence.

It reads:

- latest merged ledger,
- 27G-H3 stagnation diagnostics,
- 27G-H4 parameter sensitivity matrix,
- 27G-H5 branch review closure pack,
- optional operator cockpit snapshot.

It produces a no-order candidate discovery report and may select a candidate for **candidate-spec drafting only**. It does not register a scheduler, mutate branch state, change parameters, train, reload, paper trade, live trade, or send orders.

The next required gate is a separate 28B candidate-spec drafting and no-order shadow registration review.
