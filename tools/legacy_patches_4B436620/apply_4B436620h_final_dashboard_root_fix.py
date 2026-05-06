from __future__ import annotations

import re
from pathlib import Path

START = '# BEGIN 4B.4.3.6.6.20H FINAL DASHBOARD CONTRACT ROOT FIX'
END = '# END 4B.4.3.6.6.20H FINAL DASHBOARD CONTRACT ROOT FIX'

COMPAT_BLOCK = r