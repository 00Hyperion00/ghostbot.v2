# 4B.4.3.6.6.29A-H1 Production Report Path Hygiene Hotfix

Purpose: remove the accidentally committed `reports/production_hardeninsrc=src/` evidence path and prevent typo/shell-contaminated `--reports-dir` values from writing production hardening reports outside the canonical `reports/production_hardening/` directory.

Safety stance:

- no runtime overlay activation
- no parameter relaxation
- no scheduler mutation
- no training/reload
- no paper/live/live-real order enablement
- no HYP-006 strategy threshold mutation

Canonical evidence path remains:

```text
reports/production_hardening/
```
