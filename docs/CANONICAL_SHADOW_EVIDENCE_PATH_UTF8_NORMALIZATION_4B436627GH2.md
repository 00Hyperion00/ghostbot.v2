# 4B.4.3.6.6.27G-H2 — Canonical Shadow Evidence Path UTF-8 Normalization

This hotfix hardens HYP-005 canonical shadow evidence paths on Windows paths containing non-ASCII characters such as `Masaüstü` and `ALKILIÇ`.

It adds:

- Unicode-safe evidence path resolution,
- conservative reversible UTF-8 mojibake repair only when the repaired filesystem path exists,
- fail-closed rejection of unresolved mandatory `ledger_json`, `ledger_jsonl`, and `source_reports` paths,
- ASCII-escaped logger JSON output for Windows PowerShell 5.1 `Get-Content` display parity,
- explicit Python UTF-8 environment variables in the canonical epoch PowerShell runner.

The patch does not change scheduler cadence, trading configuration, training, reload, paper trading, live trading, or order execution permissions.
