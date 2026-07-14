# 4B436662F-H4 HYP006 Syntax Repair / Runner Import Hotfix

- Repairs malformed HYP006 wrapper tail left by previous residual patch attempts.
- Re-adds scheduler stdout/stderr PowerShell markers without runtime side effects.
- Uses importlib in the run helper so `PYTHONPATH=src` does not break the report command.
- Does not enable paper submit, network order, live real, private API access, or exchange submit.
