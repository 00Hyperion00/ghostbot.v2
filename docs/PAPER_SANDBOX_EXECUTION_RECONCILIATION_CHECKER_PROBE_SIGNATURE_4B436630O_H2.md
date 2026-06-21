# 4B.4.3.6.6.30O-H2 Reconciliation Checker Probe Signature Hotfix

This hotfix repairs the 30O checker module probe by supporting both reconciliation builder signatures:

- with `reports_dir`
- without `reports_dir`

It also updates the 30O-H1 compatibility checker to rely on 30N local reconciliation dependencies when older checker cascade statuses are stale. Runtime reconciliation behavior is unchanged.
