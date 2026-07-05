# 4B.4.3.6.6.38H-H1 Observation Metrics Source Report Selection Hotfix

This hotfix corrects the 38H source report resolver. The resolver now prefers the strict 38G main `*_ready.json` report and excludes derived artifacts such as gate, probe, contract, snapshot, guard, and not-ready reports.

Safety posture is unchanged: no runtime process start, no runtime health probe, no observation collection, no network market data, no network order, no live-real, no exchange submit, no private API, no signed request, no training/reload, no report mutation, and no Git mutation.
