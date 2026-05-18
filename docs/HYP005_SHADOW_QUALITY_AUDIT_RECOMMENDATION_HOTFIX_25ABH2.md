# 4B.4.3.6.6.25AB-H2 — HYP-005 Shadow Quality Audit Recommendation Message Consistency Hotfix

This hotfix keeps the 25AB-H1 canonical deduplication logic and fixes the recommendation text when the audit is blocked while unique shadow observations exist.

## What it fixes

- A blocked audit with unique shadow observations no longer says there were no unique observations.
- Zero-observation audits still use the no-unique-observation recommendation.
- The report includes `recommendation_consistency` metadata.
- Backward-compatible 25AB-H1 and 25AB report filenames are still written.

## Paper/live remain blocked

This patch does not train, reload, paper trade, live trade, mutate config, send orders, or allow POST requests.
