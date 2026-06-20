# 4B.4.3.6.6.30D-H2 Operator Approval Evidence Repo Hygiene Hotfix

This hotfix removes tracked patch payload artifacts from the working tree and prevents future `_patch_payload` re-additions.

It also adds a report collision guard for 30D evidence capture reports. Default input-required and explicit ready evidence runs can occur in the same second without overwriting each other.

Fail-closed guarantees:

- no paper order enablement,
- no live-real enablement,
- no runtime overlay activation,
- no training/reload,
- no scheduler mutation,
- no HYP-006 strategy threshold mutation.

30D-H1 remains the accepted functional baseline; H2 only cleans repository hygiene and preserves evidence reports.
