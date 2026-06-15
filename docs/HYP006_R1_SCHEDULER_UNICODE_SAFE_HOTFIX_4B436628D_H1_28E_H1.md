# 4B.4.3.6.6.28D-H1 / 28E-H1 Scheduler Unicode-Safe Hotfix

Fixes Windows scheduler registration and health verification failures observed after 28E:

- Unicode path escape in generated PowerShell registration scripts (`Masa\u00fcst\u00fc`).
- Scheduler action using non-absolute `python` and missing wrapper execution environment.
- Missing `--registration-json` in the scheduled canonical shadow cycle action.
- Missing `PYTHONPATH=src` in Task Scheduler runtime.
- Missing stdout/stderr scheduler logs.
- 28E JSON probe failing on UTF-8 BOM.
- 28E Windows PowerShell probe failing on localized non-UTF-8 output.

The hotfix remains no-order only. It does not create, modify, or start a scheduler task by itself.
