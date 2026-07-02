# 4B.4.3.6.6.33B Canonical Evidence & Phase Hygiene Cleanup

This patch logically cleans the project recovery view after 33A by classifying evidence and phase artifacts.

## Hard contract

- No trading action is performed.
- No training action is performed.
- No model reload is performed.
- No runtime overlay is activated.
- No paper transition is approved.
- No live-real order is approved.
- No exchange/network submit is attempted.
- No existing report, backup, payload or pycache file is deleted by this patch.

## Scope

33B produces:

- canonical phase artifact inventory excluding `__pycache__`, `_patch_backup`, `_patch_payload`, and `legacy_patches`
- report/evidence status classification
- canonical evidence index
- bad evidence ledger
- phase hygiene report

## Outputs

The runner writes three JSON artifacts under `reports/recovery`:

```text
4B436633B_canonical_evidence_phase_hygiene_<timestamp>_<ready|not_ready>.json
4B436633B_canonical_evidence_index_<timestamp>.json
4B436633B_bad_evidence_ledger_<timestamp>.json
```

## Acceptance

```text
approved_for_live_real=False
approved_for_paper_transition=False
approved_for_exchange_submit=False
approved_for_runtime_overlay=False
trading_action_performed=False
training_performed=False
reload_performed=False
```

33B is evidence/hygiene classification only. If phase/evidence blockers remain, it returns `NOT_READY` without opening any runtime path.
