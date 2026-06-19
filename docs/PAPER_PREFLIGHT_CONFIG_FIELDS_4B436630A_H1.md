# 4B.4.3.6.6.30A-H1 Paper Preflight Config Fields Hotfix

This hotfix repairs a partial 30A application where the original apply script copied the paper gate files but did not patch `Settings` because `paper_candidate_preflight_enabled` already existed from 29E.

## Guarantees

- Adds the missing 30A paper transition config fields to `Settings`.
- Keeps paper transition candidate behind operator approval.
- Keeps paper candidate, live-real, runtime activation, training/reload and trading action blocked.
- Does not mutate HYP-006 strategy thresholds or scheduler state.
