# 4B.4.3.6.6.27G-H1-H1 — Windows UTF-8 Git-Root Detection Hotfix

This hotfix corrects the repository hygiene patch on Windows paths containing non-ASCII characters such as `Masaüstü` and `ALKILIÇ`.

Git for Windows emits UTF-8 output for the relevant commands. The previous patch used locale-dependent subprocess decoding, which could turn `ü` into `Ã¼` and trigger a false `GIT_ROOT_MISMATCH`.

The hotfix applies an explicit `encoding="utf-8", errors="strict"` subprocess contract to the GH1 apply, checker, and rollback scripts. It does not modify configuration, scheduler state, trading permissions, or runtime reports.
