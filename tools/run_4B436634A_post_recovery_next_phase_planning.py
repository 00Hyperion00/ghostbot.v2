from __future__ import annotations

from tradebot.post_recovery_next_phase_planning import main

if __name__ == "__main__":
    raise SystemExit(main([*__import__('sys').argv[1:], '--write']))
