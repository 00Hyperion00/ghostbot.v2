# 4B.4.3.6.6.33G-H1 — Source 33F Completion Gate Hotfix

Purpose: fix 33G source-33F completion gate parsing.

33F may write either a check-summary schema with top-level completion flags or a full run-report schema with nested dataclass sections. 33G-H1 accepts both schemas while preserving fail-closed safety constraints.

No archive execution is authorized by this hotfix. It does not move, delete, submit, reload, train, or activate runtime overlay.
