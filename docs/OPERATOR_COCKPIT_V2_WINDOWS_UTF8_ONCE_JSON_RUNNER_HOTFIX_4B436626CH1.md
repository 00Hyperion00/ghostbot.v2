# 4B.4.3.6.6.26C-H1 — Operator Cockpit V2 — Windows UTF-8 Once-JSON Runner Output Contract Hotfix

## Scope

This overlay hotfix changes only the 26C runner `--once-json` stdout contract.

## Root cause

On Windows, regular text-mode `print()` may encode JSON with the active console locale. A parent process that correctly expects UTF-8 can then fail while decoding paths such as `Masaüstü` or messages such as `oluşmadı`.

## Repair

- Serializes the `--once-json` payload with `ensure_ascii=False`.
- Encodes JSON explicitly as UTF-8 bytes.
- Writes to `sys.stdout.buffer` and flushes immediately.
- Keeps a text-only stdout fallback for embedded or mocked environments.
- Preserves safe actions, in-memory exports, GET-only behavior, HTTP 405 mutation blocking and the existing launcher path.

## Safety

- No config mutation.
- No scheduler mutation.
- No trading action.
- No model reload.
- No paper/live enablement.
- No Binance POST request.
